from __future__ import annotations

LANGS = ("tr", "en", "de", "fr")
DEFAULT_LANG = "tr"

LANG_CURRENCY = {"tr": "TRY", "en": "USD", "de": "EUR", "fr": "EUR"}

CURRENCY_SYMBOLS = {"TRY": "₺", "EUR": "€", "USD": "$", "GBP": "£"}

# Approximate rates: 1 unit of currency = X TRY
CURRENCY_TO_TRY = {"TRY": 1.0, "EUR": 37.0, "USD": 34.0, "GBP": 43.0}

STRINGS: dict[str, dict[str, str]] = {
    "tr": {
        "site_name": "ucuzbilet.online",
        "site_tagline": "Gökyüzüne çık, dünyayı keşfet",
        "developer": "Geliştiren Ali Dinçer",
        "search_now": "Hemen ara",
        "back": "Geri",
        "help": "Yardım",
        "currency": "Para birimi",
        "currency_auto": "Dile göre otomatik",
        "language": "Dil",
        "saved_searches": "Kayıtlı aramalar",
        "no_searches": "Henüz arama yok. İlk keşfinizi oluşturun.",
        "tier_all": "Hepsi",
        "tier_lcc": "Ekonomik",
        "tier_ulcc": "Ultra ekonomik",
        "tier_fsc": "Tam hizmet",
        "tier_thy": "Sadece THY",
        "tier_lcc_tip": "Düşük maliyetli havayolu — Pegasus, easyJet, flydubai…",
        "tier_ulcc_tip": "Ultra düşük maliyet — Ryanair, Wizz Air…",
        "tier_fsc_tip": "Tam hizmet geleneksel havayolu — Lufthansa, Air France…",
        "tier_thy_tip": "Yalnızca Türk Hava Yolları uçuşları",
        "filter_stops": "Aktarma",
        "filter_airline_model": "Havayolu modeli",
        "filter_alliance": "İttifak",
        "filter_departure_country": "Çıkış ülkesi",
        "filter_destination_country": "Gidiş / varış ülkesi",
        "filter_reset": "Filtreleri sıfırla",
        "help_title": "Nasıl kullanılır?",
        "help_body": "Arama formundan kalkış ve varış seçin, tarih belirleyin ve Ara'ya basın. Sonuç sayfasında havayolu modeli, ittifak, çıkış ve gidiş ülkesi filtreleriyle fiyatları daraltın. Dil ve para birimini üst bardan değiştirebilirsiniz.",
    },
    "en": {
        "site_name": "ucuzbilet.online",
        "site_tagline": "Take off — discover the world",
        "developer": "Built by Ali Dinçer",
        "search_now": "Search now",
        "back": "Back",
        "help": "Help",
        "currency": "Currency",
        "currency_auto": "Auto by language",
        "language": "Language",
        "saved_searches": "Saved searches",
        "no_searches": "No searches yet. Create your first trip.",
        "tier_all": "All",
        "tier_lcc": "Low-cost",
        "tier_ulcc": "Ultra low-cost",
        "tier_fsc": "Full service",
        "tier_thy": "THY only",
        "tier_lcc_tip": "Low-cost carriers — Pegasus, easyJet, flydubai…",
        "tier_ulcc_tip": "Ultra low-cost — Ryanair, Wizz Air…",
        "tier_fsc_tip": "Full-service legacy airlines — Lufthansa, Air France…",
        "tier_thy_tip": "Turkish Airlines flights only",
        "filter_stops": "Stops",
        "filter_airline_model": "Airline type",
        "filter_alliance": "Alliance",
        "filter_departure_country": "Departure country",
        "filter_destination_country": "Destination country",
        "filter_reset": "Reset filters",
        "help_title": "How to use",
        "help_body": "Pick origin and destination, set dates, and search. On results, refine by airline type, alliance, departure and destination country. Change language and currency from the top bar.",
    },
    "de": {
        "site_name": "ucuzbilet.online",
        "site_tagline": "Abheben — die Welt entdecken",
        "developer": "Entwickelt von Ali Dinçer",
        "search_now": "Jetzt suchen",
        "back": "Zurück",
        "help": "Hilfe",
        "currency": "Währung",
        "currency_auto": "Automatisch (Sprache)",
        "language": "Sprache",
        "saved_searches": "Gespeicherte Suchen",
        "no_searches": "Noch keine Suche. Starten Sie Ihre erste Reise.",
        "tier_all": "Alle",
        "tier_lcc": "Billigflieger",
        "tier_ulcc": "Ultra Billig",
        "tier_fsc": "Vollservice",
        "tier_thy": "Nur THY",
        "tier_lcc_tip": "Low-Cost — Pegasus, easyJet, flydubai…",
        "tier_ulcc_tip": "Ultra Low-Cost — Ryanair, Wizz Air…",
        "tier_fsc_tip": "Vollservice — Lufthansa, Air France…",
        "tier_thy_tip": "Nur Turkish Airlines",
        "filter_stops": "Stopps",
        "filter_airline_model": "Flugzeugtyp",
        "filter_alliance": "Allianz",
        "filter_departure_country": "Abflugland",
        "filter_destination_country": "Zielland",
        "filter_reset": "Filter zurücksetzen",
        "help_title": "Anleitung",
        "help_body": "Abflug und Ziel wählen, Datum setzen, suchen. Ergebnisse nach Flugtyp, Allianz und Ländern filtern. Sprache und Währung in der oberen Leiste.",
    },
    "fr": {
        "site_name": "ucuzbilet.online",
        "site_tagline": "Décollez — explorez le monde",
        "developer": "Développé par Ali Dinçer",
        "search_now": "Rechercher",
        "back": "Retour",
        "help": "Aide",
        "currency": "Devise",
        "currency_auto": "Auto (langue)",
        "language": "Langue",
        "saved_searches": "Recherches enregistrées",
        "no_searches": "Aucune recherche. Créez votre premier voyage.",
        "tier_all": "Tous",
        "tier_lcc": "Low-cost",
        "tier_ulcc": "Ultra low-cost",
        "tier_fsc": "Service complet",
        "tier_thy": "THY seulement",
        "tier_lcc_tip": "Compagnies low-cost — Pegasus, easyJet, flydubai…",
        "tier_ulcc_tip": "Ultra low-cost — Ryanair, Wizz Air…",
        "tier_fsc_tip": "Service complet — Lufthansa, Air France…",
        "tier_thy_tip": "Vols Turkish Airlines uniquement",
        "filter_stops": "Escales",
        "filter_airline_model": "Type de compagnie",
        "filter_alliance": "Alliance",
        "filter_departure_country": "Pays de départ",
        "filter_destination_country": "Pays de destination",
        "filter_reset": "Réinitialiser",
        "help_title": "Mode d'emploi",
        "help_body": "Choisissez départ et destination, dates, puis recherchez. Filtrez par type de compagnie, alliance et pays. Langue et devise dans la barre du haut.",
    },
}


def normalize_lang(raw: str | None) -> str:
    if raw and raw.lower() in LANGS:
        return raw.lower()
    return DEFAULT_LANG


def translate(key: str, lang: str = DEFAULT_LANG) -> str:
    lng = normalize_lang(lang)
    return STRINGS.get(lng, STRINGS[DEFAULT_LANG]).get(key, STRINGS[DEFAULT_LANG].get(key, key))


def all_strings(lang: str) -> dict[str, str]:
    lng = normalize_lang(lang)
    base = dict(STRINGS[DEFAULT_LANG])
    base.update(STRINGS.get(lng, {}))
    return base
