import asyncio
from datetime import date

from app.models import FlightSearchRequest, TripType
from app.places import expand_search_origins, resolve_place
from scraper.base import ScraperSession
from scraper.skyscanner import SkyscannerScraper


async def main() -> None:
    search = FlightSearchRequest(
        name="test",
        origin_place_id="COUNTRY_ES",
        destination_place_id="MIA",
        departure_date=date(2026, 7, 4),
        return_date=date(2026, 7, 9),
        trip_type=TripType.ROUND_TRIP,
        headless=True,
    )
    origins = expand_search_origins(resolve_place("COUNTRY_ES"))
    dest = resolve_place("MIA")
    print("origins", [origin.id for origin in origins])

    session = ScraperSession(headless=True)
    await session.start()
    scraper = SkyscannerScraper()
    try:
        url = scraper._build_url(search, origins[0], dest)
        print("url", url)
        async with session.page() as page:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)
            print("title", await page.title())
            for sel in [
                "[data-testid='itinerary-card']",
                "[class*='TicketCard']",
                "[class*='FlightsTicket']",
                "[data-testid='ticket-price']",
                "span",
            ]:
                count = await page.locator(sel).count()
                print(sel, count)
            body = await page.locator("body").inner_text()
            print("body snippet", body[:1200].replace("\n", " | "))

        offers = await scraper.scrape(search, origins[0], dest, session)
        print("offers", len(offers))
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
