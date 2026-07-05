import asyncio
from datetime import UTC, datetime

from app.models import ExploreMode, ExploreSearchRequest, SavedSearch, SearchRunResult
from scraper.google_batch import GoogleBatchScraper
from scraper.exceptions import BotBlockedError

# Render'in ucretsiz plani gibi ortamlarda ters proxy/mobil baglanti zaman
# asimlari genelde 60-100 sn civarindadir; bu sinirin altinda kalip
# sonsuza kadar "donmus" gorunen bir istek yerine anlasilir bir hata donmek
# icin genis kapsamli aramalari burada kesiyoruz.
SEARCH_TIMEOUT_SECONDS = 70


async def _run_scrape(request: ExploreSearchRequest) -> tuple[list, str]:
    if request.mode == ExploreMode.FLEXIBLE and not request.use_european_hubs:
        from scraper.base import ScraperSession
        from scraper.google_explore import GoogleExploreScraper

        session = ScraperSession(headless=request.headless)
        await session.start()
        try:
            offers = await GoogleExploreScraper().scrape_flexible(request, session)
        finally:
            await session.close()
        return offers, "google_explore"

    offers = await GoogleBatchScraper().scrape_exact(request)

    SPARSE_RESULT_THRESHOLD = 3
    if len(offers) < SPARSE_RESULT_THRESHOLD and not request.use_european_hubs and request.mode in (
        ExploreMode.FIXED_TRIP,
        ExploreMode.DATE_RANGE,
    ):
        # Dogrudan sonuc hic gelmediyse veya cok azsa -- ozellikle uzak
        # bolgeler arasinda (Avrupa/Ortadogu <-> Asya/Okyanusya/Amerika/
        # Afrika) tek biletli itinerary hep bulunamayabiliyor/az cikabiliyor
        # -- Korfez/Uzakdogu/Kuzey Amerika hub'lari uzerinden ayri biletli
        # (self-transfer) kombinasyon deneniyor ve mevcut sonuclara EKLENIYOR.
        # Bu tamamen otomatik ve en fazla hub-combo'nun kendi zaman
        # butcesi kadar surer; hicbir zaman ana aramayi patlatmaz.
        try:
            from app.hub_routes import find_self_transfer_offers

            dest_place = request.destination_place()
            origin_place = request.origin_place()
            departure = request.date_from or request.departure_date
            if dest_place and origin_place and departure:
                from app.places import expand_to_airport_codes

                origin_codes = expand_to_airport_codes(origin_place, max_airports=1)
                dest_codes = expand_to_airport_codes(dest_place, max_airports=1)
                if origin_codes and dest_codes and origin_codes[0] != dest_codes[0]:
                    combo_offers = await find_self_transfer_offers(
                        request, origin_codes[0], dest_codes[0], departure
                    )
                    offers = offers + combo_offers
        except Exception:
            pass

    return offers, "google_batch"


async def run_search(saved: SavedSearch) -> list[SearchRunResult]:
    request = ExploreSearchRequest.model_validate(
        saved.model_dump(exclude={"id", "created_at", "updated_at"})
    )
    scraped_at = datetime.now(UTC).isoformat()

    try:
        try:
            offers, source = await asyncio.wait_for(
                _run_scrape(request), timeout=SEARCH_TIMEOUT_SECONDS
            )
        except ImportError:
            return [
                SearchRunResult(
                    search_id=saved.id,
                    search_name=saved.name,
                    source="google_explore",
                    status="failed",
                    message="Esnek harita modu bu sunucuda desteklenmiyor (Playwright yok). Ucus fiyat taramasi kullanin.",
                    offers=[],
                    scraped_at=scraped_at,
                )
            ]
        except TimeoutError:
            return [
                SearchRunResult(
                    search_id=saved.id,
                    search_name=saved.name,
                    source="google",
                    status="failed",
                    message="Arama cok uzun surdu ve zaman asimina ugradi. Daha dar bir tarih araligi veya hedef secip tekrar deneyin.",
                    offers=[],
                    scraped_at=scraped_at,
                )
            ]

        if offers:
            status = "success"
            message = f"{len(offers)} destinasyon bulundu."
        else:
            status = "partial"
            message = "Sonuc bulunamadi. Tarih araligini genisletin veya filteleri gevsetin."

        return [
            SearchRunResult(
                search_id=saved.id,
                search_name=saved.name,
                source=source,
                status=status,
                message=message,
                offers=offers,
                scraped_at=scraped_at,
            )
        ]
    except BotBlockedError as exc:
        return [
            SearchRunResult(
                search_id=saved.id,
                search_name=saved.name,
                source="google",
                status="failed",
                message=str(exc),
                offers=[],
                scraped_at=scraped_at,
            )
        ]
    except Exception as exc:  # noqa: BLE001
        return [
            SearchRunResult(
                search_id=saved.id,
                search_name=saved.name,
                source="google",
                status="failed",
                message=f"Tarama basarisiz: {exc}",
                offers=[],
                scraped_at=scraped_at,
            )
        ]
