"""Hub uzerinden ayri bilet (self-transfer) kombinasyon aramasi.

Direkt ucusun yaninda, Korfez / Uzakdogu / Kuzey Amerika hub havalimanlari
uzerinden iki ayri tek yon bilet (Origin->Hub, Hub->Destination) birlestirip
toplam tahmini maliyete (bilet + bagaj + bekleme cezasi) gore siralar.
"""

import asyncio
from datetime import date, datetime, timedelta

from fast_flights import FlightQuery, Passengers, create_query, get_flights

from app.models import ExploreOffer, ExploreSearchRequest, HubComboOffer
from app.places import expand_to_airport_codes, get_place
from app.regions import continent_id_by_country_code, country_name_by_code
from scraper.google_batch import (
    _airline_filter,
    _build_offer_from_flight,
    _simple_datetime_to_dt,
    _validate_flight_route,
)

# Gercek bagaj/ceza fiyat verisi yok; bu sabitler tahmini olup kolayca
# ayarlanabilir tek yerdir.
SELF_TRANSFER_BAGGAGE_ESTIMATE_TRY = 1500.0
MAX_HUB_CANDIDATES = 4
HUB_COMBO_CONCURRENCY = 6
HUB_COMBO_GATHER_TIMEOUT_SECONDS = 25
HUB_COMBO_RESULT_CAP = 10

HUB_GROUPS: dict[str, list[str]] = {
    "gulf": ["DXB", "DOH", "AUH"],
    "sea": ["SIN", "BKK", "HKG", "ICN", "KUL", "TPE", "HAN", "SGN", "DMK"],
    "na": ["JFK", "ATL", "ORD", "EWR", "YYZ"],
}

# Bu uygulamanin bolge siniflandirmasinda Turkiye "middle_east" kitasinda yer
# alir; gercek Avrupa ulkeleri ise "europe". Uzun mesafe hub degerlendirmesi
# icin ikisini de "hub'a uygun kalkis/varis" kabul ediyoruz.
_HUB_ELIGIBLE_CONTINENTS = {"europe", "middle_east"}

_GROUPS_BY_TARGET_CONTINENT: dict[str, list[str]] = {
    "asia": ["gulf", "sea"],
    "oceania": ["gulf", "sea"],
    "americas": ["na", "gulf"],
    "africa": ["gulf"],
}


def relevant_hub_groups(origin_country_code: str | None, dest_country_code: str | None) -> list[str]:
    origin_continent = continent_id_by_country_code(origin_country_code)
    dest_continent = continent_id_by_country_code(dest_country_code)
    if not origin_continent or not dest_continent or origin_continent == dest_continent:
        return []
    for near, far in ((origin_continent, dest_continent), (dest_continent, origin_continent)):
        if near in _HUB_ELIGIBLE_CONTINENTS and far in _GROUPS_BY_TARGET_CONTINENT:
            return _GROUPS_BY_TARGET_CONTINENT[far]
    return []


def pick_hub_candidates(groups: list[str], cap: int = MAX_HUB_CANDIDATES) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []
    for group in groups:
        for code in HUB_GROUPS.get(group, []):
            if code in seen:
                continue
            seen.add(code)
            candidates.append(code)
    return candidates[:cap]


def _leg_search_sync(
    origin_code: str,
    dest_code: str,
    departure: date,
    search: ExploreSearchRequest,
) -> tuple[ExploreOffer, datetime, datetime] | None:
    """Tek yonluk tek bacak icin en ucuz teklifi + kalkis/varis saatini dondurur."""
    airlines = _airline_filter(search)
    max_stops = 0 if search.direct_only else search.max_stops
    try:
        outbound = FlightQuery(
            date=departure.isoformat(),
            from_airport=origin_code,
            to_airport=dest_code,
            max_stops=max_stops,
            airlines=airlines,
        )
        query = create_query(
            flights=[outbound],
            trip="one-way",
            passengers=Passengers(adults=search.adults, children=search.children),
            seat=search.cabin_class,
            currency=search.currency,
            language="tr",
        )
        results = get_flights(query)
        if not results:
            return None

        valid = [f for f in results if _validate_flight_route(origin_code, dest_code, f.flights)]
        if not valid:
            return None
        valid.sort(key=lambda f: f.price or float("inf"))
        flight = valid[0]
        if not flight.flights:
            return None

        origin_place = get_place(origin_code)
        dest_place = get_place(dest_code)
        origin_cc = origin_place.country_code if origin_place else None
        dest_cc = dest_place.country_code if dest_place else None
        origin_country = country_name_by_code(origin_cc) or (origin_place.country if origin_place else None)
        dest_country = country_name_by_code(dest_cc) or (dest_place.country if dest_place else None)

        dep_text = departure.isoformat()
        offer = _build_offer_from_flight(
            flight,
            origin_code=origin_code,
            dest_code=dest_code,
            one_way=True,
            query=query,
            dep_text=dep_text,
            ret_text=None,
            date_summary=dep_text,
            origin_place=origin_place,
            dest_place=dest_place,
            origin_country=origin_country,
            dest_country=dest_country,
        )
        departure_dt = _simple_datetime_to_dt(flight.flights[0].departure)
        arrival_dt = _simple_datetime_to_dt(flight.flights[-1].arrival)
        return offer, departure_dt, arrival_dt
    except Exception:
        return None


def layover_penalty_try(connection_hours: float) -> float:
    if connection_hours < 2:
        return 2000.0
    if connection_hours <= 12:
        return 0.0
    if connection_hours <= 24:
        return (connection_hours - 12) * 100.0
    return 1200.0 + (connection_hours - 24) * 50.0


async def scrape_hub_combos(search: ExploreSearchRequest) -> list[HubComboOffer]:
    if not search.enable_hub_combo:
        return []

    try:
        origin_place = search.origin_place()
        dest_place = search.destination_place()
        if not dest_place:
            return []

        origin_codes = expand_to_airport_codes(origin_place, max_airports=1)
        dest_codes = expand_to_airport_codes(dest_place, max_airports=1)
        if not origin_codes or not dest_codes:
            return []
        origin_code = origin_codes[0].upper()
        dest_code = dest_codes[0].upper()
        if origin_code == dest_code:
            return []

        groups = relevant_hub_groups(origin_place.country_code, dest_place.country_code)
        if not groups:
            return []

        hub_candidates = [
            code
            for code in pick_hub_candidates(groups, cap=MAX_HUB_CANDIDATES)
            if code.upper() not in (origin_code, dest_code)
        ]
        if not hub_candidates:
            return []

        departure = search.departure_date or search.date_from
        if not departure:
            return []

        semaphore = asyncio.Semaphore(HUB_COMBO_CONCURRENCY)
        loop = asyncio.get_event_loop()

        async def build_combo(hub_code: str) -> HubComboOffer | None:
            async with semaphore:
                leg1 = await loop.run_in_executor(
                    None, _leg_search_sync, origin_code, hub_code, departure, search
                )
            if not leg1:
                return None
            offer1, _dep1, arrival1 = leg1

            offer2 = None
            departure2 = None
            connection_hours = None
            for day_offset in (0, 1):
                leg2_date = departure + timedelta(days=day_offset)
                async with semaphore:
                    leg2 = await loop.run_in_executor(
                        None, _leg_search_sync, hub_code, dest_code, leg2_date, search
                    )
                if not leg2:
                    continue
                candidate_offer2, candidate_dep2, _arr2 = leg2
                candidate_hours = (candidate_dep2 - arrival1).total_seconds() / 3600
                if candidate_hours < 0:
                    continue
                offer2, departure2, connection_hours = candidate_offer2, candidate_dep2, candidate_hours
                break

            if offer2 is None or connection_hours is None:
                return None
            if offer1.price_amount is None or offer2.price_amount is None:
                return None

            hub_place = get_place(hub_code)
            penalty = layover_penalty_try(connection_hours)
            total_cost = offer1.price_amount + offer2.price_amount + SELF_TRANSFER_BAGGAGE_ESTIMATE_TRY + penalty
            return HubComboOffer(
                leg1=offer1,
                leg2=offer2,
                hub_code=hub_code,
                hub_city=(hub_place.city or hub_place.name) if hub_place else hub_code,
                hub_country=hub_place.country if hub_place else None,
                connection_hours=round(connection_hours, 1),
                baggage_estimate=SELF_TRANSFER_BAGGAGE_ESTIMATE_TRY,
                layover_penalty=penalty,
                total_cost=total_cost,
                risky=connection_hours < 2,
            )

        tasks = [asyncio.ensure_future(build_combo(hub)) for hub in hub_candidates]
        done, pending = await asyncio.wait(tasks, timeout=HUB_COMBO_GATHER_TIMEOUT_SECONDS)
        for task in pending:
            task.cancel()

        combos: list[HubComboOffer] = []
        for task in done:
            if task.cancelled() or task.exception() is not None:
                continue
            result = task.result()
            if result is not None:
                combos.append(result)

        combos.sort(key=lambda c: c.total_cost)
        return combos[:HUB_COMBO_RESULT_CAP]
    except Exception:
        return []
