import asyncio
from urllib.parse import quote

from scraper.base import ScraperSession


async def main() -> None:
    session = ScraperSession(headless=True)
    await session.start()
    urls = [
        "https://www.google.com/travel/explore?q=" + quote("Flights from Istanbul") + "&hl=en&gl=TR",
        "https://www.google.com/travel/explore?q=" + quote("Flights from Madrid") + "&hl=en&gl=ES",
    ]
    try:
        async with session.page() as page:
            for url in urls:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(10000)
                body = await page.locator("body").inner_text()
                open("data/explore_debug.txt", "w", encoding="utf-8").write(body)
                print("url ok", "€" in body or "$" in body or "₺" in body, len(body))
                for sel in ["[data-price]", "[class*='price']", "button", "li"]:
                    c = await page.locator(sel).count()
                    if c:
                        print(sel, c)
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
