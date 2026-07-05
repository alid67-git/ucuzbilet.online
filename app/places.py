import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

PlaceType = Literal["airport", "city", "country", "hub"]


class Place(BaseModel):
    id: str
    type: PlaceType
    skyscanner: str
    google: str
    name: str
    country: str
    country_code: str
    city: str | None = None
    airports: list[str] = []
    keywords: list[str] = []


PLACES_FILE = Path(__file__).resolve().parent.parent / "data" / "places.json"

# Bir ulke/sehir "tum havalimanlari" olarak secildiginde ve arama yalnizca
# ilk N havalimanini taradiginda, N alfabetik siraya gore degil trafigi en
# yuksek havalimanlarina gore secilsin diye kullanilan oncelik sirasi.
# (orn. "Turkiye" icin alfabetik ilk 4 kod ADA/ADB/ADF/AFY olurdu ve
# Istanbul'u disarida birakirdi.) Sira onemli: her ulkede en buyuk/en cok
# baglantili havalimani en basta.
MAJOR_AIRPORT_ORDER: tuple[str, ...] = (
    # Turkiye
    "IST", "SAW", "ESB", "AYT", "ADB", "ADA", "GZT", "TZX", "DLM", "BJV",
    # Avrupa
    "LHR", "CDG", "FRA", "AMS", "MAD", "FCO", "MXP", "MUC", "BCN", "LGW",
    "ORY", "STN", "MAN", "EDI", "NCE", "DUS", "BER", "HAM", "AGP", "PMI",
    "LIN", "BGY", "VCE", "NAP", "ZRH", "GVA", "VIE", "CPH", "ARN", "OSL",
    "HEL", "DUB", "BRU", "LIS", "OPO", "WAW", "KRK", "PRG", "BUD", "ATH",
    "SKG", "OTP", "SOF", "BEG", "ZAG", "LJU", "RIX", "TLL", "VNO", "KEF",
    "GOT", "BGO",
    # Ortadogu
    "DXB", "DOH", "AUH", "JED", "RUH", "DMM", "KWI", "BAH", "MCT", "AMM",
    "BEY", "TLV", "CAI",
    # Kuzey Amerika
    "ATL", "JFK", "LAX", "ORD", "DFW", "DEN", "SFO", "SEA", "MIA", "IAH",
    "EWR", "LGA", "MCO", "BOS", "PHL", "IAD", "DCA", "LAS", "PHX", "YYZ",
    "YVR", "YUL", "MEX", "CUN",
    # Guney Amerika
    "GRU", "GIG", "EZE", "SCL", "BOG", "LIM", "UIO", "PTY",
    # Asya
    "HND", "NRT", "PEK", "PVG", "PKX", "ICN", "HKG", "SIN", "BKK", "CAN",
    "SZX", "TPE", "KUL", "DMK", "MNL", "CGK", "DPS", "DEL", "BOM", "BLR",
    "MAA", "HYD", "CCU", "KTM", "CMB", "DAC",
    # Afrika
    "JNB", "CPT", "ADD", "NBO", "LOS", "ACC", "CMN", "TUN", "ALG",
    # Okyanusya
    "SYD", "MEL", "BNE", "PER", "AKL", "NAN",
)
_MAJOR_AIRPORT_RANK: dict[str, int] = {code: rank for rank, code in enumerate(MAJOR_AIRPORT_ORDER)}


def _normalize(text: str) -> str:
    lowered = text.strip().lower()
    normalized = unicodedata.normalize("NFKD", lowered)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


@lru_cache(maxsize=1)
def _load_places() -> list[Place]:
    raw = json.loads(PLACES_FILE.read_text(encoding="utf-8"))
    return [Place.model_validate(item) for item in raw["places"]]


def get_place(place_id: str) -> Place | None:
    for place in _load_places():
        if place.id.upper() == place_id.upper():
            return place
    return None


def search_places(query: str, limit: int = 20) -> list[Place]:
    if not query.strip():
        return []

    from app.regions import load_continents

    needle = _normalize(query)
    scored: list[tuple[int, Place]] = []
    seen_ids: set[str] = set()

    for continent in load_continents():
        continent_name = _normalize(continent["name"])
        if needle == continent_name or needle in continent_name or continent_name.startswith(needle):
            for country in continent["countries"]:
                place = get_place(country["id"])
                if place and place.id not in seen_ids:
                    seen_ids.add(place.id)
                    scored.append((95, place))

    for place in _load_places():
        if place.id in seen_ids:
            continue
        haystacks = [
            place.id,
            place.name,
            place.city or "",
            place.country,
            place.google,
            place.skyscanner,
            *place.keywords,
        ]
        best = 0
        for hay in haystacks:
            normalized = _normalize(hay)
            if not normalized:
                continue
            if normalized == needle:
                best = max(best, 100)
            elif normalized.startswith(needle):
                best = max(best, 85)
            elif needle in normalized:
                best = max(best, 65)
        if best:
            type_bonus = {"country": 15, "hub": 12, "city": 8, "airport": 0}
            best += type_bonus.get(place.type, 0)
            scored.append((best, place))

    scored.sort(key=lambda item: (-item[0], item[1].type != "country", item[1].type != "city", item[1].name))
    return [place for _, place in scored[:limit]]


def resolve_place(raw: str) -> Place | None:
    if not raw or not raw.strip():
        return None

    direct = get_place(raw.strip())
    if direct:
        return direct

    needle = _normalize(raw)
    matches: list[Place] = []
    for place in _load_places():
        candidates = {
            _normalize(place.id),
            _normalize(place.google),
            _normalize(place.name),
            _normalize(place.country),
        }
        if place.city:
            candidates.add(_normalize(place.city))
        candidates.update(_normalize(keyword) for keyword in place.keywords)
        if needle in candidates:
            matches.append(place)

    if matches:
        for preferred in ("country", "hub", "city", "airport"):
            for place in matches:
                if place.type == preferred:
                    return place
        return matches[0]

    fallback = search_places(raw, limit=1)
    return fallback[0] if fallback else None


def place_label(place: Place) -> str:
    if place.type == "country":
        return f"{place.country} — Tum havalimanlari"
    if place.type == "hub":
        return place.name
    if place.type == "airport" and place.city:
        return f"{place.name} ({place.id}) — {place.city}, {place.country}"
    if place.type == "city" and place.city:
        return f"{place.city} — Tum havalimanlari ({place.country})"
    return f"{place.name} — {place.country}"


def place_children(place: Place, limit: int = 24) -> list[Place]:
    children: list[Place] = []
    if place.type in ("country", "hub"):
        seen: set[str] = set()
        if place.type == "country":
            for p in _load_places():
                if p.type == "city" and p.country_code == place.country_code:
                    children.append(p)
                    seen.add(p.id)
                    for code in p.airports:
                        seen.add(code)
        for code in place.airports:
            if code in seen:
                continue
            child = get_place(code)
            if not child or child.id in seen:
                continue
            seen.add(child.id)
            children.append(child)
            if len(children) >= limit:
                break
    elif place.type == "city":
        for code in place.airports:
            child = get_place(code)
            if child:
                children.append(child)
    return children[:limit]


def expand_to_airport_codes(place: Place, max_airports: int = 6) -> list[str]:
    if place.type == "airport":
        return [place.id]
    codes = [code for code in place.airports if get_place(code)]
    codes.sort(key=lambda code: (_MAJOR_AIRPORT_RANK.get(code, len(MAJOR_AIRPORT_ORDER)), code))
    return codes[:max_airports]


def expand_search_origins(place: Place, max_airports: int = 6) -> list[Place]:
    codes = expand_to_airport_codes(place, max_airports)
    return [p for code in codes if (p := get_place(code))]


def google_query(place: Place) -> str:
    return place.google


def airport_route_label(origin_code: str, dest_code: str) -> str:
    origin = get_place(origin_code)
    dest = get_place(dest_code)
    origin_name = origin.name if origin else origin_code
    dest_name = dest.name if dest else dest_code
    return f"{origin_name} ({origin_code}) → {dest_name} ({dest_code})"


def skyscanner_code(place: Place) -> str:
    return place.skyscanner.lower()
