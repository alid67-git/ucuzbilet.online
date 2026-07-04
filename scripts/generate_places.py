"""Tek seferlik veri uretim script'i.

data/places.json, data/regions.json ve data/explore_destinations.json
dosyalarini dunya capinda (large + medium havalimanlari, IATA kodlu,
~4500 kayit / ~235 ulke) yeniden uretir.

Mevcut 18 ulkenin elle yazilmis kayitlari (isim, etiket, keyword) AYNEN
korunur; sadece o ulkelere ait EKSIK havalimanlari eklenir. Diger tum
ulkeler sifirdan, OurAirports + airportsdata + babel verisinden uretilir.

Bu script sadece bu dosyayi calistirmak icin gerekli paketleri kullanir
(ourairports, airportsdata, babel) — bunlar uygulamanin calisma zamani
bagimliliklari DEGILDIR, requirements*.txt'e eklenmez.

Kullanim:
    pip install ourairports airportsdata babel
    python3 scripts/generate_places.py
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

import airportsdata
from babel import Locale
from ourairports.ourairports import OurAirports

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PLACES_FILE = DATA_DIR / "places.json"
REGIONS_FILE = DATA_DIR / "regions.json"
EXPLORE_FILE = DATA_DIR / "explore_destinations.json"

QUALIFYING_TYPES = {"large_airport", "medium_airport"}

MIDDLE_EAST_CODES = {
    "TR", "AE", "QA", "SA", "KW", "BH", "OM", "IL", "JO", "LB", "IQ", "YE", "SY", "PS",
}
CONTINENT_OVERRIDE = {
    "RU": "europe",
    "CY": "europe",
    "EG": "africa",
}
OURAIRPORTS_TO_BUCKET = {
    "EU": "europe",
    "NA": "americas",
    "SA": "americas",
    "AS": "asia",
    "AF": "africa",
    "OC": "oceania",
}


def _normalize_keyword(text: str) -> str:
    return text.strip().lower()


def load_existing_places() -> dict:
    raw = json.loads(PLACES_FILE.read_text(encoding="utf-8"))
    return {p["id"]: p for p in raw["places"]}


def load_existing_regions() -> dict:
    raw = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
    return raw


def build_candidate_airports() -> list[dict]:
    """OurAirports (type siniflandirmasi) + airportsdata (city/isim) birlestir."""
    oa = OurAirports()
    type_by_iata: dict[str, str] = {}
    continent_votes: dict[str, Counter] = defaultdict(Counter)
    for a in oa.airports:
        if not a.iata:
            continue
        if a.type in QUALIFYING_TYPES:
            type_by_iata[a.iata] = a.type
        if a.continent and a.continent != "AN":
            continent_votes[a.country][a.continent] += 1

    ad = airportsdata.load("IATA")

    candidates = []
    for iata, info in ad.items():
        if iata not in type_by_iata:
            continue
        candidates.append(
            {
                "iata": iata,
                "name": info.get("name") or iata,
                "city": (info.get("city") or "").strip() or None,
                "country_code": info.get("country"),
            }
        )
    return candidates, continent_votes


def continent_bucket(country_code: str, continent_votes: dict[str, Counter]) -> str | None:
    if country_code in MIDDLE_EAST_CODES:
        return "middle_east"
    if country_code in CONTINENT_OVERRIDE:
        return CONTINENT_OVERRIDE[country_code]
    votes = continent_votes.get(country_code)
    if not votes:
        return None
    top_oa_continent = votes.most_common(1)[0][0]
    return OURAIRPORTS_TO_BUCKET.get(top_oa_continent)


def turkish_country_name(country_code: str) -> str | None:
    try:
        name = Locale("tr").territories.get(country_code)
    except Exception:
        return None
    return name


def main() -> None:
    existing_places = load_existing_places()
    existing_regions = load_existing_regions()

    existing_country_ids = {
        pid for pid, p in existing_places.items() if p["type"] == "country"
    }
    existing_country_code_by_id = {
        pid: p["country_code"] for pid, p in existing_places.items() if p["type"] == "country"
    }
    existing_codes_by_country_code = {cc: cid for cid, cc in existing_country_code_by_id.items()}
    existing_country_short_name = {
        p["country_code"]: p["country"] for p in existing_places.values() if p["type"] == "country"
    }
    existing_airport_ids = {pid for pid, p in existing_places.items() if p["type"] == "airport"}

    candidates, continent_votes = build_candidate_airports()
    print(f"Aday havalimani (large+medium, IATA kodlu): {len(candidates)}")

    # Yeni ulkeleri kesfet ve isimlerini uret.
    all_country_codes = {c["country_code"] for c in candidates if c["country_code"]}
    new_country_codes = sorted(all_country_codes - set(existing_codes_by_country_code))

    country_name_tr: dict[str, str] = dict(existing_country_short_name)
    country_bucket: dict[str, str] = {}
    for cc in all_country_codes:
        bucket = continent_bucket(cc, continent_votes)
        if bucket:
            country_bucket[cc] = bucket
        if cc not in country_name_tr:
            name = turkish_country_name(cc)
            if name:
                country_name_tr[cc] = name

    new_places: dict[str, dict] = {}
    country_airport_codes: dict[str, list[str]] = defaultdict(list)
    city_groups: dict[tuple[str, str], list[str]] = defaultdict(list)

    added_airports = 0
    skipped_existing = 0

    for cand in candidates:
        iata = cand["iata"]
        cc = cand["country_code"]
        if not cc or cc not in country_name_tr:
            continue  # Turkce adi bulunamayan / gecersiz ulke kodu — atla.

        country_airport_codes[cc].append(iata)
        if cand["city"]:
            city_groups[(cand["city"].strip().lower(), cc)].append(iata)

        if iata in existing_airport_ids:
            skipped_existing += 1
            continue  # Elle yazilmis kayit korunur, uzerine yazilmaz.

        country_short = existing_country_short_name.get(cc, country_name_tr[cc])
        new_places[iata] = {
            "id": iata,
            "type": "airport",
            "skyscanner": iata.lower(),
            "google": iata,
            "name": cand["name"],
            "city": cand["city"],
            "country": country_short,
            "country_code": cc,
            "keywords": [k for k in [_normalize_keyword(cand["city"] or ""), iata.lower()] if k],
        }
        added_airports += 1

    # Sehir (city) kayitlari: ayni (sehir, ulke) ikilisini paylasan 2+ havalimani.
    existing_city_keys = set()
    for p in existing_places.values():
        if p["type"] == "city" and p.get("city") and p.get("country_code"):
            existing_city_keys.add((p["city"].strip().lower(), p["country_code"]))

    new_city_places: dict[str, dict] = {}
    for (city_lower, cc), codes in city_groups.items():
        if len(set(codes)) < 2:
            continue
        if (city_lower, cc) in existing_city_keys:
            continue  # Zaten elle yazilmis bir sehir kaydi var.
        city_display = next(
            (c["city"] for c in candidates if c["city"] and c["city"].strip().lower() == city_lower and c["country_code"] == cc),
            city_lower.title(),
        )
        country_short = existing_country_short_name.get(cc, country_name_tr[cc])
        city_id = f"CITY_{city_lower.upper().replace(' ', '_')}_{cc}"
        new_city_places[city_id] = {
            "id": city_id,
            "type": "city",
            "skyscanner": codes[0].lower(),
            "google": city_display,
            "name": f"{city_display} (Tum havalimanlari)",
            "city": city_display,
            "country": country_short,
            "country_code": cc,
            "airports": sorted(set(codes)),
            "keywords": [_normalize_keyword(city_display) + " tum"],
        }

    # Ulke kayitlari: yeni ulkeler icin sifirdan, mevcut 18 icin sadece
    # airports listesini eksik kodlarla guncelle.
    updated_existing_countries: dict[str, dict] = {}
    for cid, cc in existing_country_code_by_id.items():
        place = dict(existing_places[cid])
        all_codes = sorted(set(place.get("airports", [])) | set(country_airport_codes.get(cc, [])))
        place["airports"] = all_codes
        updated_existing_countries[cid] = place

    new_country_places: dict[str, dict] = {}
    for cc in new_country_codes:
        codes = sorted(set(country_airport_codes.get(cc, [])))
        if not codes:
            continue
        name = country_name_tr[cc]
        # Temsili google/skyscanner: ilk kod.
        rep_code = codes[0]
        country_id = f"COUNTRY_{cc}"
        new_country_places[country_id] = {
            "id": country_id,
            "type": "country",
            "skyscanner": rep_code.lower(),
            "google": name,
            "name": name,
            "country": name,
            "country_code": cc,
            "airports": codes,
            "keywords": [_normalize_keyword(name), cc.lower()],
        }

    # --- places.json birlestir ---
    final_places = []
    for pid, place in existing_places.items():
        if place["type"] == "country" and pid in updated_existing_countries:
            final_places.append(updated_existing_countries[pid])
        else:
            final_places.append(place)
    final_places.extend(new_places.values())
    final_places.extend(new_city_places.values())
    final_places.extend(new_country_places.values())

    PLACES_FILE.write_text(
        json.dumps({"places": final_places}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- regions.json ---
    continents_out = {c["id"]: dict(c, countries=list(c["countries"])) for c in existing_regions["continents"]}
    for bucket_id, bucket_name in [
        ("americas", "Amerika"),
        ("europe", "Avrupa"),
        ("middle_east", "Orta Dogu"),
        ("asia", "Asya"),
        ("africa", "Afrika"),
        ("oceania", "Okyanusya"),
    ]:
        continents_out.setdefault(bucket_id, {"id": bucket_id, "name": bucket_name, "countries": []})

    seen_country_ids = {c["id"] for cont in continents_out.values() for c in cont["countries"]}

    for cc in sorted(country_name_tr):
        country_id = existing_codes_by_country_code.get(cc, f"COUNTRY_{cc}")
        if country_id in seen_country_ids:
            continue
        bucket = country_bucket.get(cc)
        if not bucket or bucket not in continents_out:
            continue
        if not country_airport_codes.get(cc):
            continue
        continents_out[bucket]["countries"].append(
            {"id": country_id, "name": country_name_tr[cc], "country_code": cc}
        )
        seen_country_ids.add(country_id)

    REGIONS_FILE.write_text(
        json.dumps({"continents": list(continents_out.values())}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # --- explore_destinations.json: final places.json'daki her havalimani ---
    airport_country_code = {p["id"]: p["country_code"] for p in final_places if p["type"] == "airport"}
    explore_items = []
    for p in final_places:
        if p["type"] != "airport":
            continue
        cc = p["country_code"]
        region = continent_bucket(cc, continent_votes) or "asia"
        explore_items.append(
            {
                "id": p["id"],
                "name": p.get("city") or p["name"],
                "country": p["country"],
                "region": region,
            }
        )

    EXPLORE_FILE.write_text(
        json.dumps({"destinations": explore_items}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"Mevcut havalimani (korunan): {skipped_existing}")
    print(f"Yeni eklenen havalimani: {added_airports}")
    print(f"Yeni eklenen ulke: {len(new_country_places)}")
    print(f"Yeni eklenen sehir: {len(new_city_places)}")
    print(f"Toplam places: {len(final_places)}")
    print(f"Toplam explore destination: {len(explore_items)}")


if __name__ == "__main__":
    main()
