import json
from functools import lru_cache
from pathlib import Path

from app.flags import country_flag
from app.places import get_place, place_label

REGIONS_FILE = Path(__file__).resolve().parent.parent / "data" / "regions.json"


@lru_cache(maxsize=1)
def load_continents() -> list[dict]:
    raw = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    continents: list[dict] = []
    for continent in raw["continents"]:
        countries = []
        for item in continent["countries"]:
            place = get_place(item["id"])
            countries.append(
                {
                    "id": item["id"],
                    "name": item["name"],
                    "country_code": item["country_code"],
                    "flag": country_flag(item["country_code"]),
                    "label": place_label(place) if place else item["name"],
                }
            )
        continents.append(
            {
                "id": continent["id"],
                "name": continent["name"],
                "countries": countries,
            }
        )
    return continents


def continent_ids() -> list[str]:
    return [c["id"] for c in load_continents()]


def scope_label(scope_id: str) -> str:
    if scope_id == "anywhere":
        return "Her yer"
    for continent in load_continents():
        if continent["id"] == scope_id:
            return continent["name"]
    return scope_id.replace("_", " ").title()


def country_labels(country_ids: list[str]) -> list[dict]:
    labels: list[dict] = []
    for continent in load_continents():
        for country in continent["countries"]:
            if country["id"] in country_ids:
                labels.append({"id": country["id"], "name": country["name"], "flag": country["flag"]})
    return labels
