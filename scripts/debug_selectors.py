import asyncio
from urllib.parse import quote

from scraper.base import ScraperSession


async def main() -> None:
    session = ScraperSession(headless=True)
    await session.start()
    url = (
        "https://www.google.com/travel/flights/search?q="
        + quote("Flights from Madrid to Miami on 2026-07-04 returning 2026-07-09")
        + "&hl=en&gl=US"
    )
    try:
        async with session.page() as page:
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(12000)
            selectors = [
                "[role='listitem']",
                "li",
                "div[aria-label*='Top departing']",
                "div[aria-label*='flight']",
                "span:has-text('$')",
            ]
            for selector in selectors:
                print(selector, await page.locator(selector).count())
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
