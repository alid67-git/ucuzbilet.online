import json
from functools import lru_cache
from pathlib import Path

from babel import Locale, UnknownLocaleError

from app.flags import country_flag
from app.places import get_place, place_label

REGIONS_FILE = Path(__file__).resolve().parent.parent / "data" / "regions.json"

DEFAULT_REGION_LANG = "tr"


@lru_cache(maxsize=8)
def _babel_territories(lang: str) -> dict[str, str]:
    try:
        return dict(Locale.parse(lang).territories)
    except (UnknownLocaleError, ValueError):
        return {}


def localized_country_name(country_code: str | None, lang: str, fallback: str | None) -> str | None:
    """Ulke kodundan babel ile yerellestirilmis ad; bulunamazsa fallback'e (regions.json'daki
    Turkce ad) doner. lang='tr' icin dogrudan fallback kullanilir (babel'e gerek yok)."""
    if lang == DEFAULT_REGION_LANG or not country_code:
        return fallback
    name = _babel_territories(lang).get(country_code.upper())
    return name or fallback


@lru_cache(maxsize=8)
def load_continents(lang: str = DEFAULT_REGION_LANG) -> list[dict]:
    raw = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    continents: list[dict] = []
    for continent in raw["continents"]:
        countries = []
        for item in continent["countries"]:
            place = get_place(item["id"])
            name = localized_country_name(item["country_code"], lang, item["name"])
            countries.append(
                {
                    "id": item["id"],
                    "name": name,
                    "country_code": item["country_code"],
                    "flag": country_flag(item["country_code"]),
                    "label": place_label(place) if place else name,
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


def scope_label(scope_id: str, lang: str = DEFAULT_REGION_LANG) -> str:
    from app.i18n import all_strings

    key = "continent_anywhere" if scope_id == "anywhere" else "continent_" + scope_id
    translated = all_strings(lang).get(key)
    if translated:
        return translated
    for continent in load_continents():
        if continent["id"] == scope_id:
            return continent["name"]
    return scope_id.replace("_", " ").title()


def continent_id_by_country_code(country_code: str | None) -> str | None:
    if not country_code or len(country_code) != 2:
        return None
    code = country_code.upper()
    for continent in load_continents():
        for country in continent["countries"]:
            if country["country_code"] == code:
                return continent["id"]
    return None


def country_name_by_code(country_code: str | None, lang: str = DEFAULT_REGION_LANG) -> str | None:
    if not country_code or len(country_code) != 2:
        return None
    code = country_code.upper()
    for continent in load_continents():
        for country in continent["countries"]:
            if country["country_code"] == code:
                return localized_country_name(code, lang, country["name"])
    return None


def country_labels(country_ids: list[str], lang: str = DEFAULT_REGION_LANG) -> list[dict]:
    labels: list[dict] = []
    for continent in load_continents():
        for country in continent["countries"]:
            if country["id"] in country_ids:
                name = localized_country_name(country["country_code"], lang, country["name"])
                labels.append({"id": country["id"], "name": name, "flag": country["flag"]})
    return labels
