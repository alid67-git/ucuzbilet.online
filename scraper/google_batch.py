import asyncio
from datetime import date, timedelta

from fast_flights import FlightQuery, Passengers, create_query, get_flights

from app.explore_data import alliance_airlines, destination_codes_for_search, destinations_for_search, origin_codes_for_search
from app.miles import estimate_flight_miles
from app.models import ExploreMode, ExploreOffer, ExploreSearchRequest
from app.places import get_place


def _parse_price_amount(price: int | str | None) -> tuple[float | None, str]:
    if price is None:
        return None, "TRY"
    return float(price), "TRY"


def _airline_filter(search: ExploreSearchRequest) -> list[str] | None:
    if search.prefer_thy:
        return ["TK"]
    if search.alliance.value != "any":
        return alliance_airlines(search.alliance.value)
    return None


def _validate_flight_route(
    origin_code: str,
    dest_code: str,
    flights: list,
) -> bool:
    if origin_code.upper() == dest_code.upper():
        return False
    if not flights:
        return False
    first = flights[0]
    first_from = (first.from_airport.code or "").upper()
    first_to = (first.to_airport.code or "").upper()
    if first_from == first_to:
        return False
    if first_from != origin_code.upper():
        return False
    for seg in flights:
        seg_from = (seg.from_airport.code or "").upper()
        seg_to = (seg.to_airport.code or "").upper()
        if seg_from == seg_to:
            return False
    return True


def _search_sync(
    origin_code: str,
    dest_code: str,
    departure: date,
    return_date: date | None,
    search: ExploreSearchRequest,
) -> ExploreOffer | None:
    airlines = _airline_filter(search)
    max_stops = 0 if search.direct_only else search.max_stops
    one_way = search.one_way and not search.use_return_date and return_date is None

    try:
        outbound = FlightQuery(
            date=departure.isoformat(),
            from_airport=origin_code,
            to_airport=dest_code,
            max_stops=max_stops,
            airlines=airlines,
        )
        if one_way:
            query = create_query(
                flights=[outbound],
                trip="one-way",
                passengers=Passengers(adults=search.adults, children=search.children),
                seat=search.cabin_class,
                currency=search.currency,
                language="tr",
            )
        else:
            assert return_date is not None
            query = create_query(
                flights=[
                    outbound,
                    FlightQuery(
                        date=return_date.isoformat(),
                        from_airport=dest_code,
                        to_airport=origin_code,
                        max_stops=max_stops,
                        airlines=airlines,
                    ),
                ],
                trip="round-trip",
                passengers=Passengers(adults=search.adults, children=search.children),
                seat=search.cabin_class,
                currency=search.currency,
                language="tr",
            )
        results = get_flights(query)
        if not results:
            return None

        best = min(results, key=lambda f: f.price or float("inf"))
        if not _validate_flight_route(origin_code, dest_code, best.flights):
            return None

        amount, currency = _parse_price_amount(best.price)
        destinations = destinations_for_search(
            search.destination_place(),
            search.destination_scope.value,
            search.target_country_ids or None,
        )
        dest = next((d for d in destinations if d["id"] == dest_code), None)
        stops_count = max(0, len(best.flights) - 1)
        total_minutes = sum(seg.duration for seg in best.flights)
        segment_codes = [
            (seg.from_airport.code, seg.to_airport.code)
            for seg in best.flights
            if seg.from_airport.code and seg.to_airport.code
        ]
        miles = estimate_flight_miles(origin_code, dest_code, segment_codes or None)
        origin_place = get_place(origin_code)
        dest_place = get_place(dest_code)
        dep_text = departure.isoformat()
        ret_text = return_date.isoformat() if return_date else None
        date_summary = dep_text if one_way else f"{dep_text} - {ret_text}"

        return ExploreOffer(
            destination=dest_place.city or dest_place.name if dest_place else dest_code,
            destination_code=dest_code,
            destination_city=(dest_place.city or dest_place.name) if dest_place else None,
            country=dest_place.country if dest_place else (dest["country"] if dest else None),
            destination_country_code=dest_place.country_code if dest_place else None,
            origin_code=origin_code,
            origin_city=(origin_place.city or origin_place.name) if origin_place else None,
            origin_country=origin_place.country if origin_place else None,
            origin_country_code=origin_place.country_code if origin_place else None,
            region=dest["region"] if dest else None,
            price_text=f"₺{best.price:,}".replace(",", ".") if best.price else "?",
            price_amount=amount,
            currency=currency,
            miles_estimate=miles,
            date_summary=date_summary,
            departure_date=dep_text,
            return_date=ret_text,
            duration=f"{total_minutes // 60} sa {total_minutes % 60} dk",
            stops="Direkt" if stops_count == 0 else f"{stops_count} aktarma",
            airline=", ".join(best.airlines[:2]) if best.airlines else None,
            summary=f"{origin_code} → {dest_code}",
            booking_url=query.url(),
            origin_note=origin_code,
        )
    except Exception:
        return None


class GoogleBatchScraper:
    source_name = "google_batch"

    async def scrape_exact(
        self,
        search: ExploreSearchRequest,
    ) -> list[ExploreOffer]:
        origin = search.origin_place()
        max_origin = len(origin.airports) if search.use_european_hubs else 4
        origin_codes = origin_codes_for_search(origin, max_codes=max_origin)
        destinations = destinations_for_search(
            search.destination_place(),
            search.destination_scope.value,
            search.target_country_ids or None,
            max_codes=10,
        )

        departure_dates = self._build_departure_dates(search)
        tasks = []
        semaphore = asyncio.Semaphore(4)

        async def run_one(origin_code: str, dest: dict, dep: date) -> ExploreOffer | None:
            if search.one_way and not search.use_return_date:
                ret = None
            elif search.use_return_date and search.date_to and not search.flexible_departure_in_range:
                ret = search.date_to
            elif search.use_return_date and search.date_to and search.flexible_departure_in_range:
                ret = search.date_to
            else:
                ret = dep + timedelta(days=search.trip_days)
            async with semaphore:
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    _search_sync,
                    origin_code,
                    dest["id"],
                    dep,
                    ret,
                    search,
                )

        for origin_code in origin_codes:
            for dest in destinations:
                if dest["id"] == origin_code:
                    continue
                for dep in departure_dates:
                    tasks.append(run_one(origin_code, dest, dep))

        results = await asyncio.gather(*tasks)
        offers = [offer for offer in results if offer is not None]

        if search.max_price is not None:
            offers = [
                o
                for o in offers
                if o.price_amount is None or o.price_amount <= search.max_price
            ]

        best_by_dest: dict[str, ExploreOffer] = {}
        for offer in offers:
            hub_key = offer.origin_code or offer.origin_note or "?"
            dest_key = offer.destination_code or offer.destination or "?"
            key = f"{hub_key}:{dest_key}"
            existing = best_by_dest.get(key)
            if not existing or (offer.price_amount or float("inf")) < (existing.price_amount or float("inf")):
                best_by_dest[key] = offer

        sorted_offers = sorted(
            best_by_dest.values(),
            key=lambda o: o.price_amount if o.price_amount is not None else float("inf"),
        )

        if search.flexible_departure_in_range:
            return sorted_offers[: search.flexible_top_n]

        return sorted_offers[:30]

    def _anchor_departure(self, search: ExploreSearchRequest) -> date:
        if search.date_from:
            return search.date_from
        assert search.departure_date
        return search.departure_date

    def _build_departure_dates(self, search: ExploreSearchRequest) -> list[date]:
        if search.flexible_departure_in_range:
            anchor = self._anchor_departure(search)
            flex = search.flexibility_days or 3
            start = anchor - timedelta(days=flex)
            end = anchor + timedelta(days=flex)
            dates: list[date] = []
            current = start
            while current <= end:
                if search.use_return_date and search.date_to:
                    if current >= search.date_to:
                        break
                dates.append(current)
                current += timedelta(days=1)
            return dates or [anchor]

        if search.mode == ExploreMode.FIXED_TRIP and search.departure_date:
            return [search.departure_date]

        if search.mode == ExploreMode.DATE_RANGE and search.date_from:
            if search.use_return_date and search.date_to and not search.flexible_departure_in_range:
                return [search.date_from]
            anchor = search.date_from
            return [anchor]

        assert search.date_from
        return [search.date_from]
