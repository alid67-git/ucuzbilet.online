import asyncio
from datetime import date, datetime, timedelta

from fast_flights import FlightQuery, Passengers, create_query, get_flights
from fast_flights.model import SimpleDatetime, SingleFlight

from app.explore_data import alliance_airlines, canonical_country, destination_codes_for_search, destinations_for_search, origin_codes_for_search
from app.miles import estimate_flight_miles
from app.models import ExploreMode, ExploreOffer, ExploreSearchRequest
from app.places import get_place
from app.regions import country_name_by_code


def _simple_datetime_to_dt(value: SimpleDatetime) -> datetime:
    year, month, day = value.date
    hour = value.time[0] if value.time else 0
    minute = value.time[1] if len(value.time) > 1 else 0
    return datetime(year, month, day, hour, minute)


def _elapsed_minutes(segments: list[SingleFlight]) -> int:
    """Total journey time: air time plus layovers (matches Google Flights display)."""
    if not segments:
        return 0
    total = 0
    for index, segment in enumerate(segments):
        total += segment.duration
        if index + 1 >= len(segments):
            continue
        arrival = _simple_datetime_to_dt(segment.arrival)
        departure = _simple_datetime_to_dt(segments[index + 1].departure)
        if departure < arrival:
            departure += timedelta(days=1)
        total += max(0, int((departure - arrival).total_seconds() // 60))
    return total


def _split_outbound_return(
    segments: list[SingleFlight],
    dest_code: str,
) -> tuple[list[SingleFlight], list[SingleFlight]]:
    dest = dest_code.upper()
    outbound: list[SingleFlight] = []
    inbound: list[SingleFlight] = []
    past_dest = False
    for segment in segments:
        if not past_dest:
            outbound.append(segment)
            if (segment.to_airport.code or "").upper() == dest:
                past_dest = True
        else:
            inbound.append(segment)
    if not inbound:
        return segments, []
    return outbound, inbound


def _display_journey_minutes(
    segments: list[SingleFlight],
    dest_code: str,
    one_way: bool,
) -> int:
    if not segments:
        return 0
    if one_way:
        return _elapsed_minutes(segments)
    outbound, _ = _split_outbound_return(segments, dest_code)
    return _elapsed_minutes(outbound or segments)


def _format_duration(minutes: int) -> str:
    return f"{minutes // 60} sa {minutes % 60} dk"


def _layover_summary(segments: list[SingleFlight]) -> str | None:
    """Her aktarma icin havalimani ve bekleme suresini ozetler."""
    if len(segments) < 2:
        return None
    parts = []
    for index in range(len(segments) - 1):
        segment = segments[index]
        next_segment = segments[index + 1]
        arrival = _simple_datetime_to_dt(segment.arrival)
        departure = _simple_datetime_to_dt(next_segment.departure)
        if departure < arrival:
            departure += timedelta(days=1)
        wait_minutes = max(0, int((departure - arrival).total_seconds() // 60))
        airport = segment.to_airport
        code = airport.code or ""
        name = airport.name or code
        label = f"{name} ({code})" if code and code not in name else name or code
        parts.append(f"{label}: {_format_duration(wait_minutes)}")
    return " · ".join(parts)


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


MAX_AIRLINE_VARIANTS_PER_ROUTE = 6


def _is_thy_flight(flight) -> bool:
    return any("turkish airlines" in (a or "").lower() for a in (flight.airlines or []))


def _is_thy_offer(offer: ExploreOffer) -> bool:
    return bool(offer.airline) and "turkish airlines" in offer.airline.lower()


def _flight_stops_count(flight, dest_code: str) -> int:
    outbound_segments, _ = _split_outbound_return(flight.flights, dest_code)
    leg_segments = outbound_segments or flight.flights
    return max(0, len(leg_segments) - 1)


def _should_supplement_thy(search: ExploreSearchRequest) -> bool:
    if search.prefer_thy:
        return False
    return search.alliance.value in {"any", "STAR_ALLIANCE"}


def _build_route_query(
    origin_code: str,
    dest_code: str,
    departure: date,
    return_date: date | None,
    search: ExploreSearchRequest,
    *,
    airlines: list[str] | None,
    one_way: bool,
    max_stops: int | None,
):
    outbound = FlightQuery(
        date=departure.isoformat(),
        from_airport=origin_code,
        to_airport=dest_code,
        max_stops=max_stops,
        airlines=airlines,
    )
    passengers = Passengers(adults=search.adults, children=search.children)
    if one_way:
        return create_query(
            flights=[outbound],
            trip="one-way",
            passengers=passengers,
            seat=search.cabin_class,
            currency=search.currency,
            language="tr",
        )
    assert return_date is not None
    return create_query(
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
        passengers=passengers,
        seat=search.cabin_class,
        currency=search.currency,
        language="tr",
    )


def _fetch_cheapest_thy_flight(
    origin_code: str,
    dest_code: str,
    departure: date,
    return_date: date | None,
    search: ExploreSearchRequest,
    *,
    one_way: bool,
    max_stops: int | None,
):
    # Google'in varsayilan sonuc kumesi bu rota icin THY dondurmeyebilir (orn.
    # THY'nin kendi hub'i (IST) uzerinden actigi ama Google'in ilk sayfada
    # göstermedigi baglantili bir bilet). "TK" havayolu filtresiyle ayri bir
    # sorgu atarak THY'nin gercekten sattigi en ucuz secenegi ariyoruz.
    try:
        query = _build_route_query(
            origin_code,
            dest_code,
            departure,
            return_date,
            search,
            airlines=["TK"],
            one_way=one_way,
            max_stops=max_stops,
        )
        results = get_flights(query)
        if not results:
            return None, None
        valid = [
            f
            for f in results
            if _validate_flight_route(origin_code, dest_code, f.flights) and _is_thy_flight(f)
        ]
        if not valid:
            return None, None
        valid.sort(key=lambda f: f.price or float("inf"))
        return valid[0], query
    except Exception:
        return None, None


def _search_sync(
    origin_code: str,
    dest_code: str,
    departure: date,
    return_date: date | None,
    search: ExploreSearchRequest,
) -> list[ExploreOffer]:
    airlines = _airline_filter(search)
    max_stops = 0 if search.direct_only else search.max_stops
    one_way = search.one_way and not search.use_return_date and return_date is None

    try:
        query = _build_route_query(
            origin_code,
            dest_code,
            departure,
            return_date,
            search,
            airlines=airlines,
            one_way=one_way,
            max_stops=max_stops,
        )
        results = get_flights(query)
        if not results:
            return []

        valid = [f for f in results if _validate_flight_route(origin_code, dest_code, f.flights)]
        if not valid:
            return []
        valid.sort(key=lambda f: f.price or float("inf"))

        chosen: list[tuple[object, object]] = []
        seen_airlines: set[str] = set()
        for flight in valid:
            airline_key = ", ".join(flight.airlines[:2]) if flight.airlines else ""
            if airline_key in seen_airlines:
                continue
            seen_airlines.add(airline_key)
            chosen.append((flight, query))
            if len(chosen) >= MAX_AIRLINE_VARIANTS_PER_ROUTE:
                break

        # THY bu rotayi ucuyorsa "Sadece THY" filtresinde her zaman gorunsun --
        # en ucuz N farkli havayolu arasina girmese bile en ucuz THY secenegini ekle.
        # Genel sorguda hic THY yoksa, THY'ye ozel ek bir sorguyla tekrar denenir.
        if not any(_is_thy_flight(f) for f, _ in chosen):
            cheapest_thy = next((f for f in valid if _is_thy_flight(f)), None)
            thy_query = query
            if cheapest_thy is None and _should_supplement_thy(search):
                cheapest_thy, thy_query = _fetch_cheapest_thy_flight(
                    origin_code,
                    dest_code,
                    departure,
                    return_date,
                    search,
                    one_way=one_way,
                    max_stops=max_stops,
                )
            if cheapest_thy is not None and thy_query is not None:
                chosen.append((cheapest_thy, thy_query))

        # Yukaridaki garanti sadece "en ucuz" THY secenegini ekliyor -- THY'nin
        # ucuz ama aktarmali bir bileti varsa, daha pahali olsa da direkt THY
        # secenegi hic gorunmeyebilir ("Direkt" + "Sadece THY" filtresi birlikte
        # kullanildiginda satir kaybolur). Direkt bir THY ucusu ayri olarak
        # garanti edilir.
        if max_stops != 0 and not any(
            _is_thy_flight(f) and _flight_stops_count(f, dest_code) == 0 for f, _ in chosen
        ):
            direct_thy = next(
                (f for f in valid if _is_thy_flight(f) and _flight_stops_count(f, dest_code) == 0),
                None,
            )
            direct_thy_query = query
            if direct_thy is None and _should_supplement_thy(search):
                direct_thy, direct_thy_query = _fetch_cheapest_thy_flight(
                    origin_code,
                    dest_code,
                    departure,
                    return_date,
                    search,
                    one_way=one_way,
                    max_stops=0,
                )
            if direct_thy is not None and direct_thy_query is not None:
                chosen.append((direct_thy, direct_thy_query))

        destinations = destinations_for_search(
            search.destination_place(),
            search.destination_scope.value,
            search.target_country_ids or None,
        )
        dest = next((d for d in destinations if d["id"] == dest_code), None)
        origin_place = get_place(origin_code)
        dest_place = get_place(dest_code)
        dep_text = departure.isoformat()
        ret_text = return_date.isoformat() if return_date else None
        date_summary = dep_text if one_way else f"{dep_text} - {ret_text}"

        dest_cc = dest_place.country_code if dest_place else None
        origin_cc = origin_place.country_code if origin_place else None
        dest_country = country_name_by_code(dest_cc) or (
            canonical_country(dest_code, dest["country"] if dest else None)
            if not dest_place
            else (country_name_by_code(dest_cc) or dest_place.country)
        )
        origin_country = country_name_by_code(origin_cc) or (
            origin_place.country if origin_place else None
        )

        offers = []
        for flight, booking_query in chosen:
            amount, currency = _parse_price_amount(flight.price)
            outbound_segments, _ = _split_outbound_return(flight.flights, dest_code)
            leg_segments = outbound_segments or flight.flights
            stops_count = max(0, len(leg_segments) - 1)
            total_minutes = _display_journey_minutes(flight.flights, dest_code, one_way)
            segment_codes = [
                (seg.from_airport.code, seg.to_airport.code)
                for seg in flight.flights
                if seg.from_airport.code and seg.to_airport.code
            ]
            miles = estimate_flight_miles(origin_code, dest_code, segment_codes or None)
            offers.append(
                ExploreOffer(
                    destination=dest_place.city or dest_place.name if dest_place else dest_code,
                    destination_code=dest_code,
                    destination_city=(dest_place.city or dest_place.name) if dest_place else None,
                    country=dest_country,
                    destination_country_code=dest_cc,
                    origin_code=origin_code,
                    origin_city=(origin_place.city or origin_place.name) if origin_place else None,
                    origin_country=origin_country,
                    origin_country_code=origin_cc,
                    region=dest["region"] if dest else None,
                    price_text=f"₺{flight.price:,}".replace(",", ".") if flight.price else "?",
                    price_amount=amount,
                    currency=currency,
                    miles_estimate=miles,
                    date_summary=date_summary,
                    departure_date=dep_text,
                    return_date=ret_text,
                    duration=_format_duration(total_minutes),
                    duration_minutes=total_minutes,
                    stops="Direkt" if stops_count == 0 else f"{stops_count} aktarma",
                    stops_count=stops_count,
                    layover_summary=_layover_summary(leg_segments),
                    airline=", ".join(flight.airlines[:2]) if flight.airlines else None,
                    summary=f"{origin_code} → {dest_code}",
                    booking_url=booking_query.url(),
                    origin_note=origin_code,
                )
            )
        return offers
    except Exception:
        return []


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
            target_airport_ids=search.target_airport_ids or None,
        )

        departure_dates = self._build_departure_dates(search)
        tasks = []
        semaphore = asyncio.Semaphore(4)

        async def run_one(origin_code: str, dest: dict, dep: date) -> list[ExploreOffer]:
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
        offers = [offer for sublist in results for offer in sublist]

        if search.max_price is not None:
            offers = [
                o
                for o in offers
                if o.price_amount is None or o.price_amount <= search.max_price
            ]

        def price_key(o: ExploreOffer) -> float:
            return o.price_amount if o.price_amount is not None else float("inf")

        grouped: dict[str, list[ExploreOffer]] = {}
        for offer in offers:
            hub_key = offer.origin_code or offer.origin_note or "?"
            dest_key = offer.destination_code or offer.destination or "?"
            key = f"{hub_key}:{dest_key}"
            grouped.setdefault(key, []).append(offer)
        for group in grouped.values():
            group.sort(key=price_key)

        if search.flexible_departure_in_range:
            single_best = [group[0] for group in grouped.values()]
            return sorted(single_best, key=price_key)

        multi_offers: list[ExploreOffer] = []
        for group in grouped.values():
            seen_airlines: set[str] = set()
            group_chosen: list[ExploreOffer] = []
            for offer in group:
                airline_key = offer.airline or ""
                if airline_key in seen_airlines:
                    continue
                seen_airlines.add(airline_key)
                group_chosen.append(offer)
                if len(seen_airlines) >= MAX_AIRLINE_VARIANTS_PER_ROUTE:
                    break

            # THY bu rotayi ucuyorsa "Sadece THY" filtresinde her zaman gorunsun.
            if not any(_is_thy_offer(o) for o in group_chosen):
                cheapest_thy = next((o for o in group if _is_thy_offer(o)), None)
                if cheapest_thy is not None:
                    group_chosen.append(cheapest_thy)

            multi_offers.extend(group_chosen)

        # Genel 120 sonuc sinirlamasi, fiyatca ucuz olmayan hub'lardaki
        # garanti THY secenegini disarida birakabiliyor -- oysa "Sadece THY"
        # filtresinin butun amaci her hub'daki THY secenegini
        # karsilastirabilmek. THY'li teklifler bu sinirlamadan muaf tutulur.
        thy_offers = [o for o in multi_offers if _is_thy_offer(o)]
        other_offers = [o for o in multi_offers if not _is_thy_offer(o)]
        remaining_slots = max(0, 120 - len(thy_offers))
        combined = thy_offers + sorted(other_offers, key=price_key)[:remaining_slots]
        return sorted(combined, key=price_key)

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
