import asyncio
from datetime import date

from app.models import FlightSearchRequest, TripType
from app.places import resolve_place
from scraper.base import ScraperSession
from scraper.google_flights import GoogleFlightsScraper


async def main() -> None:
    search = FlightSearchRequest(
        name="test",
        origin_place_id="MAD",
        destination_place_id="MIA",
        departure_date=date(2026, 7, 4),
        return_date=date(2026, 7, 9),
        trip_type=TripType.ROUND_TRIP,
        headless=True,
    )
    session = ScraperSession(headless=True)
    await session.start()
    try:
        offers = await GoogleFlightsScraper().scrape(
            search, resolve_place("MAD"), resolve_place("MIA"), session
        )
        print("offers", len(offers))
        for offer in offers[:3]:
            print(offer.price_text, offer.origin_note)
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
