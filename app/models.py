from datetime import date
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.places import Place, get_place, place_label, resolve_place


class ExploreMode(str, Enum):
    FLEXIBLE = "flexible"
    DATE_RANGE = "date_range"
    FIXED_TRIP = "fixed_trip"
    HUB_TO_COUNTRY = "hub_to_country"  # legacy — use_european_hubs + fixed/date moduna donusturulur


class AllianceFilter(str, Enum):
    ANY = "any"
    STAR_ALLIANCE = "STAR_ALLIANCE"
    ONEWORLD = "ONEWORLD"
    SKYTEAM = "SKYTEAM"


class DestinationScope(str, Enum):
    ANYWHERE = "anywhere"
    EUROPE = "europe"
    AMERICAS = "americas"
    MIDDLE_EAST = "middle_east"
    ASIA = "asia"


class ExploreSearchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    origin_place_id: str = ""
    origin_label: str = ""
    destination_place_id: str | None = None
    destination_label: str = ""
    use_european_hubs: bool = False
    mode: ExploreMode = ExploreMode.FIXED_TRIP
    date_from: date | None = None
    date_to: date | None = None
    departure_date: date | None = None
    trip_days: int = Field(default=5, ge=1, le=30)
    flexible_departure_in_range: bool = False
    flexibility_days: int = Field(default=3, ge=0, le=14)
    use_return_date: bool = False
    one_way: bool = False
    flexible_top_n: int = Field(default=3, ge=1, le=10)
    destination_scope: DestinationScope = DestinationScope.ANYWHERE
    target_country_ids: list[str] = Field(default_factory=list)
    alliance: AllianceFilter = AllianceFilter.ANY
    prefer_thy: bool = False
    max_stops: int | None = Field(default=None, ge=0, le=2)
    direct_only: bool = False
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=9)
    max_price: int | None = Field(default=None, ge=0)
    cabin_class: Literal["economy", "premium-economy", "business", "first"] = "economy"
    currency: str = "TRY"
    headless: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> "ExploreSearchRequest":
        if self.direct_only and self.max_stops is None:
            self.max_stops = 0

        if self.prefer_thy:
            self.alliance = AllianceFilter.ANY

        if not self.use_return_date:
            self.one_way = True
            self.date_to = None
        else:
            self.one_way = False

        if self.mode == ExploreMode.HUB_TO_COUNTRY:
            self.use_european_hubs = True
            if self.date_from and self.date_to:
                self.mode = ExploreMode.DATE_RANGE
            else:
                self.mode = ExploreMode.FIXED_TRIP

        if self.use_european_hubs:
            hub = get_place("HUB_EU")
            self.origin_place_id = "HUB_EU"
            self.origin_label = place_label(hub) if hub else "Avrupa hub havalimanlari"
        elif str(self.origin_place_id).upper() == "HUB_EU":
            self.use_european_hubs = True
            hub = get_place("HUB_EU")
            self.origin_label = place_label(hub) if hub else "Avrupa hub havalimanlari"
        else:
            origin = resolve_place(self.origin_place_id)
            if not origin:
                raise ValueError("Gecerli bir kalkis noktasi secin.")
            if not self.origin_label:
                self.origin_label = place_label(origin)

        if self.destination_place_id:
            dest = resolve_place(self.destination_place_id)
            if dest and not self.destination_label:
                self.destination_label = place_label(dest)
            self.destination_scope = DestinationScope.ANYWHERE
            self.target_country_ids = []

        if self.mode == ExploreMode.FIXED_TRIP:
            if not self.departure_date and not self.date_from:
                raise ValueError("Gidis tarihi gerekli.")
            if not self.departure_date and self.date_from:
                self.departure_date = self.date_from
            if self.flexible_departure_in_range:
                if self.flexibility_days <= 0:
                    self.flexibility_days = 3
                if not self.date_from:
                    self.date_from = self.departure_date
            if self.use_return_date:
                self.one_way = False
                if not self.date_to:
                    raise ValueError("Donus tarihi secildi ama tarih girilmedi.")
                if self.date_to <= (self.departure_date or self.date_from):
                    raise ValueError("Donus tarihi gidisten sonra olmali.")
                span = (self.date_to - (self.departure_date or self.date_from)).days
                self.trip_days = span
            elif self.one_way:
                self.date_to = None
        elif self.mode == ExploreMode.DATE_RANGE:
            if not self.date_from:
                raise ValueError("Gidis tarihi gerekli.")
            if self.use_return_date:
                self.one_way = False
                if not self.date_to:
                    raise ValueError("Donus tarihi gerekli.")
                if self.date_to <= self.date_from:
                    raise ValueError("Donus tarihi gidisten sonra olmali.")
                if not self.flexible_departure_in_range:
                    span = (self.date_to - self.date_from).days
                    if span > 30:
                        raise ValueError("Seyahat suresi en fazla 30 gun olabilir.")
                    self.trip_days = span
            elif not self.flexible_departure_in_range and not self.one_way:
                pass
            elif not self.flexible_departure_in_range and self.one_way:
                self.date_to = None
            elif not self.flexible_departure_in_range:
                raise ValueError("Donus tarihi secin, tek gidiş secin veya kalis suresi ile gidiş-donuş kullanin.")
            if self.flexible_departure_in_range and self.flexibility_days <= 0:
                self.flexibility_days = 3
            if self.flexible_departure_in_range and not self.use_return_date:
                if self.flexibility_days <= 0:
                    self.flexibility_days = 3
        elif self.mode == ExploreMode.FLEXIBLE and self.use_european_hubs:
            raise ValueError("Hub modu esnek taramayla kullanilamaz; belirli gun veya tarih araligi secin.")

        return self

    def origin_place(self) -> Place:
        place = resolve_place(self.origin_place_id)
        if not place:
            raise ValueError("Kalkis noktasi bulunamadi.")
        return place

    def destination_place(self) -> Place | None:
        if not self.destination_place_id:
            return None
        return resolve_place(self.destination_place_id)


class ExploreOffer(BaseModel):
    destination: str
    destination_code: str | None = None
    destination_city: str | None = None
    country: str | None = None
    destination_country_code: str | None = None
    origin_code: str | None = None
    origin_city: str | None = None
    origin_country: str | None = None
    origin_country_code: str | None = None
    region: str | None = None
    price_text: str
    price_amount: float | None = None
    currency: str | None = None
    miles_estimate: int | None = None
    date_summary: str | None = None
    departure_date: str | None = None
    return_date: str | None = None
    duration: str | None = None
    duration_minutes: int | None = None
    stops: str | None = None
    stops_count: int | None = None
    airline: str | None = None
    summary: str | None = None
    booking_url: str | None = None
    origin_note: str | None = None


class SearchRunResult(BaseModel):
    search_id: str
    search_name: str
    source: str = "google_explore"
    status: Literal["success", "partial", "failed"]
    message: str
    offers: list[ExploreOffer] = Field(default_factory=list)
    scraped_at: str


class SavedSearch(ExploreSearchRequest):
    id: str
    created_at: str
    updated_at: str
