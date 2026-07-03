import re

from app.flags import country_flag
from app.miles import estimate_flight_miles
from app.models import ExploreOffer
from app.places import get_place


def _code_from_summary(summary: str | None, index: int) -> str | None:
    if not summary or "→" not in summary:
        return None
    parts = [part.strip() for part in summary.split("→")]
    if index >= len(parts):
        return None
    part = parts[index]
    match = re.search(r"\(([A-Z]{3})\)", part)
    if match:
        return match.group(1)
    token = part.split()[0] if part else ""
    if len(token) == 3 and token.isalpha():
        return token.upper()
    return None


def format_miles(value: int | None) -> str:
    if value is None:
        return ""
    return f"{value:,}".replace(",", ".")


def route_display(offer: ExploreOffer) -> dict:
    origin_code = (offer.origin_code or _code_from_summary(offer.summary, 0) or "").upper() or None
    dest_code = (offer.destination_code or _code_from_summary(offer.summary, 1) or "").upper() or None

    origin_place = get_place(origin_code) if origin_code else None
    dest_place = get_place(dest_code) if dest_code else None

    origin_city = offer.origin_city or (origin_place.city if origin_place else None) or (
        origin_place.name if origin_place else None
    )
    origin_country = offer.origin_country or (origin_place.country if origin_place else None)
    origin_country_code = offer.origin_country_code or (origin_place.country_code if origin_place else None)

    dest_city = offer.destination_city or (dest_place.city if dest_place else None)
    if not dest_city and dest_place:
        dest_city = dest_place.name
    if not dest_city and offer.destination:
        dest_city = offer.destination.split("—")[0].split("(")[0].strip()

    dest_country = offer.country or (dest_place.country if dest_place else None)
    dest_country_code = offer.destination_country_code or (dest_place.country_code if dest_place else None)

    miles = offer.miles_estimate
    if miles is None and origin_code and dest_code:
        miles = estimate_flight_miles(origin_code, dest_code)

    return {
        "origin_code": origin_code,
        "destination_code": dest_code,
        "origin_city": origin_city or origin_code,
        "origin_country": origin_country,
        "origin_country_code": origin_country_code,
        "origin_flag": country_flag(origin_country_code),
        "destination_city": dest_city or dest_code,
        "destination_country": dest_country,
        "destination_country_code": dest_country_code,
        "destination_flag": country_flag(dest_country_code),
        "miles_estimate": miles,
        "miles_text": format_miles(miles),
    }
