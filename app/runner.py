from datetime import UTC, datetime

from app.models import ExploreMode, ExploreSearchRequest, SavedSearch, SearchRunResult
from scraper.base import ScraperSession
from scraper.google_batch import GoogleBatchScraper
from scraper.google_explore import GoogleExploreScraper
from scraper.exceptions import BotBlockedError


async def run_search(saved: SavedSearch) -> list[SearchRunResult]:
    request = ExploreSearchRequest.model_validate(
        saved.model_dump(exclude={"id", "created_at", "updated_at"})
    )
    scraped_at = datetime.now(UTC).isoformat()

    try:
        if request.mode == ExploreMode.FLEXIBLE and not request.use_european_hubs:
            session = ScraperSession(headless=request.headless)
            await session.start()
            try:
                offers = await GoogleExploreScraper().scrape_flexible(request, session)
                source = "google_explore"
            finally:
                await session.close()
        else:
            offers = await GoogleBatchScraper().scrape_exact(request)
            source = "google_batch"

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
