"""Great-circle mesafe ile tahmini status mili (Miles&Smiles benzeri)."""

from math import asin, cos, radians, sin, sqrt

# IATA -> (enlem, boylam)
AIRPORT_COORDS: dict[str, tuple[float, float]] = {
    "IST": (41.275, 28.752),
    "SAW": (40.898, 29.309),
    "ESB": (40.128, 32.995),
    "ADB": (38.292, 27.157),
    "AYT": (36.899, 30.801),
    "DLM": (36.713, 28.792),
    "FCO": (41.800, 12.239),
    "CIA": (41.799, 12.594),
    "MXP": (45.631, 8.723),
    "LIN": (45.445, 9.276),
    "BGY": (45.674, 9.704),
    "VCE": (45.505, 12.352),
    "NAP": (40.884, 14.291),
    "FLR": (43.810, 11.205),
    "JFK": (40.641, -73.778),
    "EWR": (40.693, -74.169),
    "LGA": (40.777, -73.873),
    "MIA": (25.795, -80.290),
    "LAX": (33.942, -118.408),
    "LHR": (51.470, -0.454),
    "LGW": (51.153, -0.182),
    "CDG": (49.010, 2.550),
    "ORY": (48.723, 2.380),
    "AMS": (52.310, 4.768),
    "FRA": (50.037, 8.562),
    "MUC": (48.354, 11.786),
    "MAD": (40.472, -3.561),
    "BCN": (41.297, 2.078),
    "VIE": (48.110, 16.570),
    "ZRH": (47.458, 8.555),
    "BRU": (50.901, 4.484),
    "DOH": (25.261, 51.565),
    "DXB": (25.253, 55.365),
    "AGP": (36.675, -4.499),
}


def _haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = radians(a[0]), radians(a[1])
    lat2, lon2 = radians(b[0]), radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 3958.8 * 2 * asin(sqrt(h))


def estimate_flight_miles(origin_code: str, dest_code: str, segment_codes: list[tuple[str, str]] | None = None) -> int | None:
    """Ucus mesafesine gore tahmini mil. Google mil bilgisi vermediginde kullanilir."""
    if segment_codes:
        total = 0.0
        for from_code, to_code in segment_codes:
            a = AIRPORT_COORDS.get(from_code.upper())
            b = AIRPORT_COORDS.get(to_code.upper())
            if not a or not b:
                continue
            total += _haversine_miles(a, b)
        return int(round(total)) if total > 0 else None

    a = AIRPORT_COORDS.get(origin_code.upper())
    b = AIRPORT_COORDS.get(dest_code.upper())
    if not a or not b:
        return None
    return int(round(_haversine_miles(a, b)))
