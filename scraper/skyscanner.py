import re

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.models import FlightOffer, FlightSearchRequest, TripType
from app.places import Place, skyscanner_code
from scraper.base import BaseFlightScraper, ScraperSession
from scraper.exceptions import BotBlockedError


class SkyscannerScraper(BaseFlightScraper):
    source_name = "skyscanner"

    async def scrape(
        self,
        search: FlightSearchRequest,
        origin: Place,
        destination: Place,
        session: ScraperSession,
    ) -> list[FlightOffer]:
        async with session.page() as page:
            url = self._build_url(search, origin, destination)
            await page.goto(url, wait_until="domcontentloaded")
            await self._accept_cookies(page)
            await self._wait_for_results(page)

            body = (await page.locator("body").inner_text()).lower()
            if self._is_bot_page(body):
                raise BotBlockedError(
                    "Skyscanner bot kontrolu gosterdi. 'Tarayiciyi gorunur ac' secip tekrar deneyin "
                    "veya kaynak olarak Google Flights secin."
                )

            return self._post_filter(await self._extract_offers(page, origin, destination), search)

    @staticmethod
    def _is_bot_page(body: str) -> bool:
        markers = (
            "are you a person or a robot",
            "robot olmadiginizi",
            "bot",
            "captcha",
            "challenge",
        )
        return any(marker in body for marker in markers)

    def _build_url(self, search: FlightSearchRequest, origin: Place, destination: Place) -> str:
        origin_code = skyscanner_code(origin)
        dest_code = skyscanner_code(destination)
        dep = search.departure_date.strftime("%y%m%d")

        if search.trip_type == TripType.ROUND_TRIP and search.return_date:
            ret = search.return_date.strftime("%y%m%d")
            path = f"{origin_code}/{dest_code}/{dep}/{ret}/"
        else:
            path = f"{origin_code}/{dest_code}/{dep}/"

        cabin_map = {
            "economy": "economy",
            "premium_economy": "premiumeconomy",
            "business": "business",
            "first": "first",
        }
        cabin = cabin_map.get(search.cabin_class, "economy")
        params = [
            f"adultsv2={search.adults}",
            f"childrenv2={search.children}",
            f"infantsv2={search.infants}",
            f"cabinclass={cabin}",
            "preferdirects=true" if search.direct_only else "preferdirects=false",
            "rtn=1" if search.trip_type == TripType.ROUND_TRIP and search.return_date else "rtn=0",
        ]
        return "https://www.skyscanner.com.tr/transport/flights/" + path + "?" + "&".join(params)

    async def _wait_for_results(self, page) -> None:
        selectors = [
            "[data-testid='itinerary-card']",
            "[class*='TicketCard']",
            "[class*='FlightsTicket']",
            "button:has-text('Seç')",
            "button:has-text('Select')",
        ]
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=12000)
                return
            except PlaywrightTimeoutError:
                continue

    async def _extract_offers(self, page, origin: Place, destination: Place) -> list[FlightOffer]:
        offers: list[FlightOffer] = []
        current_url = page.url

        cards = page.locator("[data-testid='itinerary-card'], [class*='TicketCard'], [class*='FlightsTicket']")
        count = await cards.count()
        limit = min(count, 12)

        for index in range(limit):
            card = cards.nth(index)
            text = (await card.inner_text()).strip()
            if not text:
                continue

            lines = [line.strip() for line in text.splitlines() if line.strip()]
            price_line = next(
                (line for line in lines if any(token in line for token in ("₺", "TL", "€", "$"))),
                None,
            )
            if not price_line:
                continue

            amount, currency = self._parse_price(price_line)
            airline = next((line for line in lines if 2 < len(line) <= 40 and "₺" not in line and "€" not in line and "$" not in line), None)
            duration = next((line for line in lines if "s" in line and ("dk" in line or "sa" in line)), None)
            stops = next((line for line in lines if "aktarmasiz" in line.lower() or "direkt" in line.lower() or "stop" in line.lower()), None)

            offers.append(
                FlightOffer(
                    source=self.source_name,
                    price_text=price_line,
                    price_amount=amount,
                    currency=currency,
                    airline=airline,
                    duration=duration,
                    stops=stops,
                    summary=" | ".join(lines[:5]),
                    booking_url=current_url,
                    origin_note=f"{origin.name} → {destination.name}",
                )
            )

        offers.sort(key=lambda item: item.price_amount if item.price_amount is not None else float("inf"))
        deduped: list[FlightOffer] = []
        seen: set[str] = set()
        for offer in offers:
            if offer.price_text in seen:
                continue
            seen.add(offer.price_text)
            deduped.append(offer)
        return deduped[:12]
