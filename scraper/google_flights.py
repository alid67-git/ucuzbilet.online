import re
from urllib.parse import quote

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.models import FlightOffer, FlightSearchRequest, TripType
from app.places import Place, google_query
from scraper.base import BaseFlightScraper, ScraperSession


class BotBlockedError(Exception):
    pass


class GoogleFlightsScraper(BaseFlightScraper):
    source_name = "google_flights"

    async def scrape(
        self,
        search: FlightSearchRequest,
        origin: Place,
        destination: Place,
        session: ScraperSession,
    ) -> list[FlightOffer]:
        async with session.page() as page:
            await self._run_search(page, search, origin, destination)

            if search.direct_only:
                await self._apply_direct_filter(page)

            if search.airlines:
                await self._apply_airline_filters(page, search.airlines)

            await self._wait_for_results(page)
            offers = await self._extract_offers(page, origin, destination)
            return self._post_filter(offers, search)

    async def _run_search(self, page, search: FlightSearchRequest, origin: Place, destination: Place) -> None:
        origin_text = google_query(origin)
        destination_text = google_query(destination)
        dep = search.departure_date.isoformat()
        ret = search.return_date.isoformat() if search.return_date else None

        if search.trip_type == TripType.ONE_WAY or not ret:
            query = f"Flights from {origin_text} to {destination_text} on {dep}"
        else:
            query = f"Flights from {origin_text} to {destination_text} on {dep} returning {ret}"

        gl = self._country_gl(origin.country_code)
        url = (
            "https://www.google.com/travel/flights/search?q="
            + quote(query)
            + f"&hl=en&gl={gl}"
        )
        await page.goto(url, wait_until="domcontentloaded")
        await self._accept_cookies(page)

    @staticmethod
    def _country_gl(country_code: str) -> str:
        return country_code if country_code in {"TR", "ES", "IT", "US", "GB", "FR", "DE"} else "US"

    async def _wait_for_results(self, page) -> None:
        markers = [
            "text=Search results",
            "text=Top departing flights",
            "text=round trip",
            "span:has-text('$')",
            "span:has-text('€')",
            "span:has-text('₺')",
        ]
        for marker in markers:
            try:
                await page.wait_for_selector(marker, timeout=20000)
                await page.wait_for_timeout(1500)
                return
            except PlaywrightTimeoutError:
                continue

    async def _apply_direct_filter(self, page) -> None:
        for label in ["Stops", "Nonstop"]:
            button = page.get_by_role("button", name=re.compile(label, re.I))
            if await button.count():
                await button.first.click()
                await page.wait_for_timeout(500)
                for option in ["Nonstop only", "Direct only"]:
                    opt = page.get_by_text(option, exact=False)
                    if await opt.count():
                        await opt.first.click()
                        await page.wait_for_timeout(800)
                        return
                await page.keyboard.press("Escape")
                return

    async def _apply_airline_filters(self, page, airlines: list[str]) -> None:
        button = page.get_by_role("button", name=re.compile("Airlines", re.I))
        if await button.count():
            await button.first.click()
            await page.wait_for_timeout(500)
            for airline in airlines:
                text_opt = page.get_by_text(airline, exact=False)
                if await text_opt.count():
                    await text_opt.first.click()
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(800)

    async def _extract_offers(self, page, origin: Place, destination: Place) -> list[FlightOffer]:
        offers: list[FlightOffer] = []
        current_url = page.url
        body = await page.locator("body").inner_text()

        route_hint = f"{origin.id}–{destination.id}".upper()
        route_hint_alt = f"{origin.id}-{destination.id}".upper()

        chunks = re.split(r"(?=round trip)", body)
        for chunk in chunks:
            if route_hint not in chunk.upper() and route_hint_alt not in chunk.upper():
                if google_query(origin).lower() not in chunk.lower():
                    continue
                if google_query(destination).lower() not in chunk.lower():
                    continue

            price_match = re.search(r"([$€₺]\s?[\d,]+)", chunk)
            if not price_match:
                continue

            price_text = price_match.group(1).strip()
            amount, currency = self._parse_price(price_text)
            lines = [line.strip() for line in chunk.splitlines() if line.strip()]
            airline = next(
                (
                    line
                    for line in lines
                    if 2 < len(line) <= 40
                    and not re.search(r"[\d:]|stop|hr|min|kg|CO2|round trip|[$€₺]", line, re.I)
                ),
                None,
            )
            duration = next((line for line in lines if "hr" in line.lower() or "min" in line.lower()), None)
            stops = next((line for line in lines if "stop" in line.lower() or "nonstop" in line.lower()), None)

            offers.append(
                FlightOffer(
                    source=self.source_name,
                    price_text=price_text,
                    price_amount=amount,
                    currency=currency,
                    airline=airline,
                    duration=duration,
                    stops=stops,
                    summary=" | ".join(lines[:6]),
                    booking_url=current_url,
                    origin_note=f"{origin.name} → {destination.name}",
                )
            )

        if not offers:
            cards = page.locator("li").filter(has_text=re.compile(r"[$€₺]\s?\d"))
            count = min(await cards.count(), 12)
            for index in range(count):
                text = (await cards.nth(index).inner_text()).strip()
                price_match = re.search(r"([$€₺]\s?[\d,]+)", text)
                if not price_match:
                    continue
                price_text = price_match.group(1)
                amount, currency = self._parse_price(price_text)
                offers.append(
                    FlightOffer(
                        source=self.source_name,
                        price_text=price_text,
                        price_amount=amount,
                        currency=currency,
                        summary=text.replace("\n", " | ")[:200],
                        booking_url=current_url,
                        origin_note=f"{origin.name} → {destination.name}",
                    )
                )

        offers.sort(key=lambda item: item.price_amount if item.price_amount is not None else float("inf"))
        deduped: list[FlightOffer] = []
        seen: set[str] = set()
        for offer in offers:
            key = f"{offer.price_text}-{offer.airline}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(offer)
        return deduped[:12]
