import asyncio
from urllib.parse import quote

from scraper.base import ScraperSession


async def main() -> None:
    session = ScraperSession(headless=True)
    await session.start()
    queries = [
        "https://www.google.com/travel/flights/search?q=" + quote("Flights from MAD to MIA on 2026-07-04 returning 2026-07-09"),
        "https://www.google.com/travel/flights/search?q=" + quote("Flights from Madrid to Miami on 2026-07-04 returning 2026-07-09") + "&hl=en&gl=US",
    ]
    try:
        async with session.page() as page:
            for url in queries:
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(8000)
                body = await page.locator("body").inner_text()
                open("data/debug_url.txt", "w", encoding="utf-8").write(body)
                has_mia = "miami" in body.lower() or "mia" in body.lower()
                has_mad = "madrid" in body.lower() or "mad" in body.lower()
                print(url[:80], "mia", has_mia, "mad", has_mad, "list", await page.locator("[role=listitem]").count())
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
