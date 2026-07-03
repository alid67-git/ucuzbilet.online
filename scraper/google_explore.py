import re
from urllib.parse import quote

from playwright.async_api import Page

from app.explore_data import list_destinations, origin_codes_for_search
from app.models import AllianceFilter, ExploreOffer, ExploreSearchRequest
from app.places import google_query
from scraper.base import ScraperSession


class GoogleExploreScraper:
    source_name = "google_explore"

    async def scrape_flexible(
        self,
        search: ExploreSearchRequest,
        session: ScraperSession,
    ) -> list[ExploreOffer]:
        origin = search.origin_place()
        origin_text = google_query(origin)
        if len(origin_text) == 3 and origin.city:
            origin_text = origin.city

        async with session.page() as page:
            url = (
                "https://www.google.com/travel/explore?q="
                + quote(f"Flights from {origin_text}")
                + "&hl=en&gl=TR&curr=TRY"
            )
            await page.goto(url, wait_until="domcontentloaded")
            await self._accept_cookies(page)
            await self._apply_filters(page, search)
            await page.wait_for_timeout(5000)
            body = await page.locator("body").inner_text()
            offers = self._parse_explore_body(body, page.url, origin.name)
            return self._post_filter(offers, search)

    async def _accept_cookies(self, page: Page) -> None:
        for label in ["Accept all", "Tümünü kabul et", "Kabul et"]:
            button = page.get_by_role("button", name=label)
            if await button.count():
                await button.first.click()
                await page.wait_for_timeout(400)
                return

    async def _apply_filters(self, page: Page, search: ExploreSearchRequest) -> None:
        if search.direct_only or search.max_stops == 0:
            stops_btn = page.get_by_role("button", name=re.compile("Stops|Aktarma", re.I))
            if await stops_btn.count():
                await stops_btn.first.click()
                await page.wait_for_timeout(500)
                for label in ["Nonstop only", "Nonstop", "Aktarmasiz"]:
                    opt = page.get_by_text(label, exact=False)
                    if await opt.count():
                        await opt.first.click()
                        await page.wait_for_timeout(1500)
                        break
                await page.keyboard.press("Escape")

        if search.alliance != AllianceFilter.ANY:
            airlines_btn = page.get_by_role("button", name=re.compile("Airlines|Havayolu", re.I))
            if await airlines_btn.count():
                await airlines_btn.first.click()
                await page.wait_for_timeout(500)
                labels = {
                    AllianceFilter.STAR_ALLIANCE: "Star Alliance",
                    AllianceFilter.ONEWORLD: "Oneworld",
                    AllianceFilter.SKYTEAM: "SkyTeam",
                }
                opt = page.get_by_text(labels.get(search.alliance, ""), exact=False)
                if await opt.count():
                    await opt.first.click()
                    await page.wait_for_timeout(1500)
                await page.keyboard.press("Escape")

        if search.prefer_thy:
            airlines_btn = page.get_by_role("button", name=re.compile("Airlines|Havayolu", re.I))
            if await airlines_btn.count():
                await airlines_btn.first.click()
                await page.wait_for_timeout(500)
                for label in ["Turkish Airlines", "Turk Hava Yollari", "THY"]:
                    opt = page.get_by_text(label, exact=False)
                    if await opt.count():
                        await opt.first.click()
                        await page.wait_for_timeout(1500)
                        break
                await page.keyboard.press("Escape")

    def _parse_explore_body(self, body: str, url: str, origin_name: str) -> list[ExploreOffer]:
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        skip = {
            "Explore", "Flights", "Hotels", "Round trip", "Economy", "Where to?",
            "All filters", "Flights only", "Stops", "Price", "Airlines", "Duration",
            "About these results", "Loading results", "Sign in", "Vacation rentals", "Bags",
            "Change appearance", "Skip to main content", "Accessibility feedback",
        }
        offers: list[ExploreOffer] = []

        for index, line in enumerate(lines):
            if not re.search(r"TRY\s?[\d.,]+|[$€₺]\s?[\d.,]+", line, re.I):
                continue

            price_line = line
            context = lines[max(0, index - 4) : index]
            city = None
            date_summary = None
            stops = None
            duration = None

            for ctx in reversed(context):
                if ctx in skip:
                    continue
                if re.search(r"hr|min|sa|dk", ctx, re.I):
                    duration = duration or ctx
                    continue
                if re.search(r"nonstop|stop|aktarma|direkt", ctx, re.I):
                    stops = stops or ctx
                    continue
                if re.search(r"\d|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec", ctx):
                    date_summary = date_summary or ctx
                    continue
                if len(ctx) <= 35 and city is None:
                    city = ctx

            if not city:
                continue

            amount, currency = _parse_price(price_line)
            dest_meta = next(
                (d for d in list_destinations("anywhere") if d["name"].lower() == city.lower()),
                None,
            )
            offers.append(
                ExploreOffer(
                    destination=city,
                    destination_code=dest_meta["id"] if dest_meta else None,
                    country=dest_meta["country"] if dest_meta else None,
                    region=dest_meta["region"] if dest_meta else None,
                    price_text=price_line,
                    price_amount=amount,
                    currency=currency,
                    miles_estimate=self._estimate_miles(search, dest_meta["id"] if dest_meta else None),
                    date_summary=date_summary,
                    duration=duration,
                    stops=stops,
                    summary=" | ".join(context + [price_line]),
                    booking_url=url,
                    origin_note=f"Kalkis: {origin_name}",
                )
            )

        offers.sort(key=lambda o: o.price_amount if o.price_amount is not None else float("inf"))
        return offers

    def _post_filter(self, offers: list[ExploreOffer], search: ExploreSearchRequest) -> list[ExploreOffer]:
        from app.explore_data import destination_codes_for_search
        from app.models import DestinationScope
        from app.places import expand_to_airport_codes

        filtered = offers
        if search.target_country_ids and not search.destination_place():
            from app.explore_data import destinations_from_countries

            allowed = {item["id"].upper() for item in destinations_from_countries(search.target_country_ids, max_per_country=12)}
            filtered = [
                o
                for o in filtered
                if (o.destination_code and o.destination_code.upper() in allowed)
            ]
        elif search.destination_scope != DestinationScope.ANYWHERE:
            scope = search.destination_scope.value
            filtered = [o for o in filtered if o.region == scope]

        dest = search.destination_place()
        if dest:
            allowed = {code.upper() for code in expand_to_airport_codes(dest, max_airports=12)}
            dest_names = {d["name"].lower() for d in destination_codes_for_search(dest)}
            dest_country = dest.country.lower()
            filtered = [
                o
                for o in filtered
                if (o.destination_code and o.destination_code.upper() in allowed)
                or (o.destination and o.destination.lower() in dest_names)
                or (o.country and o.country.lower() == dest_country)
                or (o.destination and dest_country in o.destination.lower())
            ]

        if search.max_price is not None:
            filtered = [
                o
                for o in filtered
                if o.price_amount is None or o.currency != "TRY" or o.price_amount <= search.max_price
            ]
        return filtered[:25]

    def _estimate_miles(self, search: ExploreSearchRequest, dest_code: str | None) -> int | None:
        from app.explore_data import origin_codes_for_search
        from app.miles import estimate_flight_miles

        if not dest_code:
            return None
        origins = origin_codes_for_search(search.origin_place(), max_codes=1)
        if not origins:
            return None
        origin_code = origins[0]
        if len(origin_code) != 3:
            return None
        return estimate_flight_miles(origin_code, dest_code)


def _parse_price(text: str) -> tuple[float | None, str | None]:
    cleaned = text.replace("\u202f", " ").replace("\xa0", " ").strip()
    currency = None
    if "₺" in cleaned or "TRY" in cleaned.upper() or "TL" in cleaned.upper():
        currency = "TRY"
        match = re.search(r"TRY\s?([\d.,]+)|₺\s?([\d.,]+)|([\d.,]+)\s?(?:TL|TRY)", cleaned, re.I)
    elif "€" in cleaned:
        currency = "EUR"
        match = re.search(r"[\d.,]+", cleaned)
    elif "$" in cleaned:
        currency = "USD"
        match = re.search(r"[\d.,]+", cleaned)
    else:
        match = re.search(r"[\d.,]+", cleaned)

    if currency == "TRY" and match:
        raw = next(g for g in match.groups() if g)
        amount = float(raw.replace(".", "").replace(",", "."))
        return amount, currency

    if not match:
        return None, currency
    raw = match.group(0) if hasattr(match, "group") else match
    if currency == "TRY":
        amount = float(raw.replace(".", "").replace(",", "."))
    else:
        amount = float(raw.replace(",", ""))
    return amount, currency
