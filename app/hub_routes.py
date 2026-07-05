"""Dogrudan/tek biletli sonuc bulunamayan uzun mesafe rotalar icin yedek arama.

Avrupa/Ortadogu <-> Asya/Okyanusya/Amerika/Afrika gibi uzak bolgeler arasinda
Google Flights bazen tek bir rezervasyonla satin alinabilir itinerary
dondurmuyor. Bu modul, boyle durumlarda Korfez/Uzakdogu/Kuzey Amerika
hub havalimanlari uzerinden iki ayri tek yon bilet (self-transfer)
kombinasyonu deneyip en ucuzlarini normal bir ExploreOffer olarak dondurur.
"""

import asyncio
from datetime import date, timedelta

from fast_flights import get_flights

from app.models import ExploreOffer, ExploreSearchRequest
from app.places import get_place
from app.regions import continent_id_by_country_code
from scraper.google_batch import (
    _airline_filter,
    _build_route_query,
    _parse_price_amount,
    _simple_datetime_to_dt,
    _validate_flight_route,
)

# Gercek bagaj/aktarma cezasi verisi yok; kolayca ayarlanabilir tek sabit.
SELF_TRANSFER_BAGGAGE_ESTIMATE_TRY = 1500.0
MAX_HUB_CANDIDATES = 3
HUB_COMBO_CONCURRENCY = 4
HUB_COMBO_RESULT_CAP = 3
HUB_COMBO_TIME_BUDGET_SECONDS = 25
MIN_CONNECTION_HOURS = 1.5
MAX_CONNECTION_HOURS = 30

HUB_GROUPS: dict[str, list[str]] = {
    "gulf": ["DXB", "DOH", "AUH"],
    "sea": ["SIN", "BKK", "HKG", "ICN"],
    "na": ["JFK", "ATL", "ORD"],
}

# Bu uygulamanin bolge siniflandirmasinda Turkiye "middle_east" kitasinda;
# gercek Avrupa ulkeleri "europe". Uzun mesafe hub degerlendirmesi icin
# ikisi de "hub'a uygun kalkis/varis" sayilir.
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


def _pick_hub_candidates(groups: list[str], exclude: set[str], cap: int = MAX_HUB_CANDIDATES) -> list[str]:
    seen: set[str] = set()
    candidates: list[str] = []
    for group in groups:
        for code in HUB_GROUPS.get(group, []):
            if code in seen or code in exclude:
                continue
            seen.add(code)
            candidates.append(code)
    return candidates[:cap]


def _leg_sync(origin_code: str, dest_code: str, departure: date, search: ExploreSearchRequest) -> dict | None:
    """Tek yonluk tek bacak icin en ucuz gecerli teklifi + saatlerini dondurur."""
    try:
        airlines = _airline_filter(search)
        query = _build_route_query(
            origin_code,
            dest_code,
            departure,
            None,
            search,
            airlines=airlines,
            one_way=True,
            max_stops=None,
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
        amount, currency = _parse_price_amount(flight.price)
        if amount is None:
            return None
        return {
            "amount": amount,
            "currency": currency,
            "airline": ", ".join(flight.airlines[:2]) if flight.airlines else None,
            "departure_dt": _simple_datetime_to_dt(flight.flights[0].departure),
            "arrival_dt": _simple_datetime_to_dt(flight.flights[-1].arrival),
            "stops_count": max(0, len(flight.flights) - 1),
        }
    except Exception:
        return None


async def find_self_transfer_offers(
    search: ExploreSearchRequest,
    origin_code: str,
    dest_code: str,
    departure: date,
) -> list[ExploreOffer]:
    origin_place = get_place(origin_code)
    dest_place = get_place(dest_code)
    if not origin_place or not dest_place:
        return []

    groups = relevant_hub_groups(origin_place.country_code, dest_place.country_code)
    if not groups:
        return []

    hub_candidates = _pick_hub_candidates(groups, exclude={origin_code.upper(), dest_code.upper()})
    if not hub_candidates:
        return []

    loop = asyncio.get_event_loop()
    semaphore = asyncio.Semaphore(HUB_COMBO_CONCURRENCY)

    async def build_combo(hub_code: str) -> ExploreOffer | None:
        async with semaphore:
            leg1 = await loop.run_in_executor(None, _leg_sync, origin_code, hub_code, departure, search)
        if not leg1:
            return None

        for day_offset in (0, 1):
            leg2_date = departure + timedelta(days=day_offset)
            async with semaphore:
                leg2 = await loop.run_in_executor(None, _leg_sync, hub_code, dest_code, leg2_date, search)
            if not leg2:
                continue
            connection_hours = (leg2["departure_dt"] - leg1["arrival_dt"]).total_seconds() / 3600
            if connection_hours < MIN_CONNECTION_HOURS or connection_hours > MAX_CONNECTION_HOURS:
                continue

            hub_place = get_place(hub_code)
            hub_city = (hub_place.city or hub_place.name) if hub_place else hub_code
            total_amount = leg1["amount"] + leg2["amount"] + SELF_TRANSFER_BAGGAGE_ESTIMATE_TRY
            total_minutes = int((leg2["arrival_dt"] - leg1["departure_dt"]).total_seconds() // 60)
            conn_h = int(connection_hours)
            conn_m = int(round((connection_hours - conn_h) * 60))
            airline_text = ", ".join(filter(None, [leg1["airline"], leg2["airline"]])) or None

            return ExploreOffer(
                destination=dest_place.city or dest_place.name,
                destination_code=dest_code,
                destination_city=dest_place.city or dest_place.name,
                country=dest_place.country,
                destination_country_code=dest_place.country_code,
                origin_code=origin_code,
                origin_city=origin_place.city or origin_place.name,
                origin_country=origin_place.country,
                origin_country_code=origin_place.country_code,
                price_text=f"₺{round(total_amount):,}".replace(",", "."),
                price_amount=total_amount,
                currency="TRY",
                date_summary=departure.isoformat(),
                departure_date=departure.isoformat(),
                duration=f"{total_minutes // 60} sa {total_minutes % 60} dk",
                duration_minutes=total_minutes,
                stops="1 aktarma (ayri bilet)",
                stops_count=1,
                layover_summary=f"{hub_city} ({hub_code}): {conn_h} sa {conn_m} dk",
                airline=airline_text,
                summary=f"{origin_code} → {dest_code}",
                is_self_transfer=True,
            )
        return None

    tasks = [asyncio.ensure_future(build_combo(hub)) for hub in hub_candidates]
    try:
        done, pending = await asyncio.wait(tasks, timeout=HUB_COMBO_TIME_BUDGET_SECONDS)
    except Exception:
        for task in tasks:
            task.cancel()
        return []
    for task in pending:
        task.cancel()

    combos: list[ExploreOffer] = []
    for task in done:
        if task.cancelled() or task.exception() is not None:
            continue
        result = task.result()
        if result is not None:
            combos.append(result)

    combos.sort(key=lambda o: o.price_amount if o.price_amount is not None else float("inf"))
    return combos[:HUB_COMBO_RESULT_CAP]


async def find_separate_oneway_offers(
    search: ExploreSearchRequest,
    origin_code: str,
    dest_code: str,
    departure: date,
    return_date: date,
) -> list[ExploreOffer]:
    """Gidis-donus aramasi az sonuc dondurduğünde, ayni rotanin gidis ve
    donusunu (hub'siz) AYRI birer tek yon bilet olarak sorgular. Havayollari
    bazen gidis-donus fiyatlandirmasinda gostermedigi ucuz secenekleri tek
    yonlu aramada gosteriyor; bu da gercek bir "ayri bilet al" stratejisidir."""
    origin_place = get_place(origin_code)
    dest_place = get_place(dest_code)
    if not origin_place or not dest_place:
        return []

    loop = asyncio.get_event_loop()
    outbound, inbound = await asyncio.gather(
        loop.run_in_executor(None, _leg_sync, origin_code, dest_code, departure, search),
        loop.run_in_executor(None, _leg_sync, dest_code, origin_code, return_date, search),
    )
    if not outbound or not inbound:
        return []

    total_amount = outbound["amount"] + inbound["amount"]
    outbound_minutes = int((outbound["arrival_dt"] - outbound["departure_dt"]).total_seconds() // 60)
    airline_text = ", ".join(filter(None, [outbound["airline"], inbound["airline"]])) or None
    stops_count = max(outbound["stops_count"], inbound["stops_count"])

    return [
        ExploreOffer(
            destination=dest_place.city or dest_place.name,
            destination_code=dest_code,
            destination_city=dest_place.city or dest_place.name,
            country=dest_place.country,
            destination_country_code=dest_place.country_code,
            origin_code=origin_code,
            origin_city=origin_place.city or origin_place.name,
            origin_country=origin_place.country,
            origin_country_code=origin_place.country_code,
            price_text=f"₺{round(total_amount):,}".replace(",", "."),
            price_amount=total_amount,
            currency="TRY",
            date_summary=f"{departure.isoformat()} - {return_date.isoformat()}",
            departure_date=departure.isoformat(),
            return_date=return_date.isoformat(),
            duration=f"{outbound_minutes // 60} sa {outbound_minutes % 60} dk",
            duration_minutes=outbound_minutes,
            stops="Direkt" if stops_count == 0 else f"{stops_count} aktarma",
            stops_count=stops_count,
            airline=airline_text,
            summary=f"{origin_code} → {dest_code}",
            is_self_transfer=True,
        )
    ]
