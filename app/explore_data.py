import json
from functools import lru_cache
from pathlib import Path

from app.places import Place, expand_search_origins, expand_to_airport_codes, get_place, google_query, place_label

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "explore_destinations.json"


@lru_cache(maxsize=1)
def _load() -> dict:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def list_destinations(scope: str = "anywhere") -> list[dict]:
    items = _load()["destinations"]
    if scope == "anywhere":
        return items
    return [item for item in items if item["region"] == scope]


def destination_codes_for_search(
    destination: Place | None,
    scope: str = "anywhere",
    max_codes: int = 8,
) -> list[dict]:
    if destination:
        codes = expand_to_airport_codes(destination, max_airports=max_codes)
        results: list[dict] = []
        for code in codes:
            place = get_place(code)
            if not place:
                continue
            meta = next((d for d in list_destinations("anywhere") if d["id"] == code), None)
            results.append(
                {
                    "id": code,
                    "name": place_label(place),
                    "country": place.country,
                    "region": meta["region"] if meta else None,
                }
            )
        if results:
            return results

    return list_destinations(scope)


def destinations_from_countries(country_ids: list[str], max_per_country: int = 6) -> list[dict]:
    seen: set[str] = set()
    results: list[dict] = []
    for country_id in country_ids:
        place = get_place(country_id)
        if not place:
            continue
        for item in destination_codes_for_search(place, "anywhere", max_codes=max_per_country):
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            results.append(item)
    return results


def destinations_for_search(
    destination: Place | None,
    scope: str,
    target_country_ids: list[str] | None = None,
    max_codes: int = 8,
) -> list[dict]:
    if destination:
        return destination_codes_for_search(destination, scope, max_codes=max_codes)
    if target_country_ids:
        expanded = destinations_from_countries(target_country_ids, max_per_country=max_codes)
        if expanded:
            return expanded
    return list_destinations(scope)


def origin_codes_for_search(origin: Place, max_codes: int = 6) -> list[str]:
    expanded = expand_search_origins(origin, max_airports=max_codes)
    codes: list[str] = []
    for place in expanded:
        code = google_query(place)
        if len(code) == 3 and code.isalpha():
            codes.append(code.upper())
        else:
            codes.append(code)
    return codes or [google_query(origin)]


def alliance_airlines(alliance: str) -> list[str] | None:
    if alliance in {"STAR_ALLIANCE", "ONEWORLD", "SKYTEAM"}:
        return [alliance]
    return None
