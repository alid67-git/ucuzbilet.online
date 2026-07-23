import asyncio
import logging
from datetime import UTC, datetime

from app.models import ExploreMode, ExploreSearchRequest, SavedSearch, SearchRunResult
from scraper.google_batch import GoogleBatchScraper
from scraper.exceptions import BotBlockedError

logger = logging.getLogger(__name__)


def _offer_fingerprint(offer) -> tuple:
    return (
        offer.origin_code,
        offer.destination_code,
        offer.airline,
        offer.stops_count,
        round(offer.price_amount) if offer.price_amount is not None else None,
    )


def _merge_unique(offers: list, new_offers: list, seen: set) -> list:
    """Ayni ucusun (ayni kalkis/varis/havayolu/aktarma/fiyat) birden fazla
    garanti mekanizmasi tarafindan bulunup ikilenmesini onler."""
    merged = list(offers)
    for offer in new_offers:
        fp = _offer_fingerprint(offer)
        if fp in seen:
            continue
        seen.add(fp)
        merged.append(offer)
    return merged

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
    seen_offers = {_offer_fingerprint(o) for o in offers}

    SPARSE_RESULT_THRESHOLD = 3
    if request.mode in (
        ExploreMode.FIXED_TRIP,
        ExploreMode.DATE_RANGE,
    ):
        # Dogrudan sonuc hic gelmediyse veya cok azsa yedek aramalar deneniyor.
        # Bunlarin hicbiri ana aramayi patlatmaz (try/except ile sarili) ve
        # toplamda disaridaki SEARCH_TIMEOUT_SECONDS butcesi icinde kalir.
        try:
            dest_place = request.destination_place()
            origin_place = request.origin_place()
            departure = request.date_from or request.departure_date
            if dest_place and origin_place and departure:
                from app.places import expand_to_airport_codes

                origin_codes = expand_to_airport_codes(origin_place, max_airports=1)
                dest_codes = expand_to_airport_codes(dest_place, max_airports=1)
                if origin_codes and dest_codes and origin_codes[0] != dest_codes[0]:
                    origin_code, dest_code = origin_codes[0], dest_codes[0]
                    return_date = request.date_to if request.use_return_date and request.date_to else None

                    if len(offers) < SPARSE_RESULT_THRESHOLD:
                        # 1) Gidis-donus sorgusu az sonuc dondurdugunde, ayni rotanin
                        # gidis ve donusunu ayri birer tek yon bilet olarak sorgular
                        # -- gidis-donus fiyatlandirmasinda gorunmeyen ucuz/farkli
                        # havayolu secenekleri boylece yakalanabiliyor.
                        if request.use_return_date and request.date_to:
                            from app.hub_routes import find_separate_oneway_offers

                            oneway_offers = await find_separate_oneway_offers(
                                request, origin_code, dest_code, departure, request.date_to
                            )
                            offers = _merge_unique(offers, oneway_offers, seen_offers)

                        # 2) Uzak bolgeler arasinda (Avrupa/Ortadogu <-> Asya/
                        # Okyanusya/Amerika/Afrika) tek biletli itinerary hep
                        # bulunamayabiliyor -- Korfez/Uzakdogu/Kuzey Amerika
                        # hub'lari uzerinden ayri biletli (self-transfer)
                        # kombinasyon deneniyor.
                        if len(offers) < SPARSE_RESULT_THRESHOLD:
                            from app.hub_routes import find_self_transfer_offers

                            combo_offers = await find_self_transfer_offers(
                                request, origin_code, dest_code, departure
                            )
                            offers = _merge_unique(offers, combo_offers, seen_offers)

                    # 3) Direkt ucus garantisi: yukaridaki adimlar toplam sonuc
                    # sayisina bagli calisir, ama "hic direkt ucus yok" ayri bir
                    # sorun -- ana toplu taramada belirli bir havalimaninin
                    # (orn. SAW) sorgulari o an bos donebilir (Google tarafi
                    # degiskenligi) ve boylece o havalimanindan gercekte var
                    # olan bir direkt ucus (orn. AJet/Pegasus nonstop, THY
                    # nonstop) hic denenmeden atlanabilir. Bu yuzden en olasi
                    # 2 kalkis havalimaninda (orn. IST, SAW), sonuc sayisindan
                    # bagimsiz olarak, hem THY'ye ozel hem havayolu-bagimsiz
                    # birer direkt-ucus denemesi paralel yapiliyor.
                    from scraper.google_batch import _is_thy_offer, _search_sync, _should_supplement_thy

                    # Kalkis icin en olasi 2 havalimani (orn. IST, SAW), varis
                    # icin de (genelde tek sehrin butun havalimanlari, orn.
                    # Milano: MXP/LIN/BGY) en fazla 3 havalimani deneniyor --
                    # ucuz havayollari genelde o sehrin "birincil" havalimanina
                    # degil (orn. MXP) ikincil birine (orn. BGY) direkt uctugu
                    # icin varis tarafinda da birden fazla secenek denemek
                    # gerekiyor.
                    origin_codes_top = expand_to_airport_codes(origin_place, max_airports=2)
                    dest_codes_top = expand_to_airport_codes(dest_place, max_airports=3)

                    # "Bir yerde direkt ucus var mi" sorusu havalimani bazinda
                    # sorulmali -- IST'ten direkt bir THY ucusu bulunmus olmasi,
                    # SAW'dan da direkt bir ucus (orn. AJet/Pegasus) oldugunu
                    # garantilemez. Bu yuzden her kalkis havalimani ayri ayri
                    # kontrol edilip sadece direkt secenegi HENUZ olmayanlar
                    # icin sorgu atiliyor.
                    origins_with_direct_thy = {
                        o.origin_code for o in offers if _is_thy_offer(o) and o.stops_count == 0
                    }
                    origins_with_direct_any = {
                        o.origin_code for o in offers if o.stops_count == 0
                    }

                    thy_pairs = [
                        (oc, dest_code)
                        for oc in origin_codes_top
                        if oc != dest_code and oc not in origins_with_direct_thy
                    ]
                    direct_pairs = [
                        (oc, dc)
                        for oc in origin_codes_top
                        for dc in dest_codes_top
                        if oc != dc and oc not in origins_with_direct_any
                    ]

                    loop = asyncio.get_event_loop()
                    tasks = []
                    task_kinds = []
                    if thy_pairs and _should_supplement_thy(request):
                        # THY genelde bir sehrin ikincil/ucuz havalimanina degil
                        # ana havalimanina uctugu icin sadece birincil varis
                        # kodu (dest_code) denenir.
                        thy_direct_search = request.model_copy(update={"prefer_thy": True, "direct_only": True})
                        for oc, dc in thy_pairs:
                            tasks.append(
                                loop.run_in_executor(
                                    None, _search_sync, oc, dc, departure, return_date, thy_direct_search
                                )
                            )
                            task_kinds.append(("thy", oc))
                    if direct_pairs:
                        # Ucuz havayollari genelde sehrin ikincil havalimanina
                        # (orn. Milano icin BGY) direkt uctugu icin varis
                        # tarafinda birden fazla havalimani deneniyor.
                        plain_direct_search = request.model_copy(update={"direct_only": True})
                        for oc, dc in direct_pairs:
                            tasks.append(
                                loop.run_in_executor(
                                    None, _search_sync, oc, dc, departure, return_date, plain_direct_search
                                )
                            )
                            task_kinds.append(("direct", oc))

                    if tasks:
                        gathered = await asyncio.gather(*tasks, return_exceptions=True)
                        added: set[tuple[str, str]] = set()
                        for (kind, oc), result in zip(task_kinds, gathered):
                            if isinstance(result, BaseException) or not result:
                                continue
                            key = (kind, oc)
                            if key in added:
                                continue
                            offers = _merge_unique(offers, result[:1], seen_offers)
                            added.add(key)

                    # Direkt THY bulunamadiysa, aktarmali olsa bile THY'nin
                    # "Sadece THY" filtresinde en az bir kez gorunmesini
                    # garantile (onceki davranis).
                    if not any(_is_thy_offer(o) for o in offers) and _should_supplement_thy(request):
                        thy_search = request.model_copy(update={"prefer_thy": True})
                        thy_offers = await loop.run_in_executor(
                            None, _search_sync, origin_code, dest_code, departure, return_date, thy_search
                        )
                        if thy_offers:
                            offers = _merge_unique(offers, thy_offers[:1], seen_offers)
        except Exception:
            logger.exception("Az sonuc / THY garanti fallback'i basarisiz oldu")

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
