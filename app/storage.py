import json
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import ValidationError

from app.models import ExploreSearchRequest, SavedSearch, SearchRunResult
from app.places import place_label, resolve_place

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEARCHES_DIR = DATA_DIR / "searches"
RESULTS_DIR = DATA_DIR / "results"
QUICK_SEARCH_ID = "quick"


def ensure_data_dirs() -> None:
    SEARCHES_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def migrate_legacy_search_data(data: dict) -> dict:
    """Eski skyscanner/google_flights kayitlarini yeni explore formatina cevirir."""
    updated = dict(data)

    if not updated.get("origin_place_id"):
        for key in ("origin", "origin_label"):
            raw = updated.get(key)
            if raw:
                place = resolve_place(str(raw))
                if place:
                    updated["origin_place_id"] = place.id
                    updated["origin_label"] = place_label(place)
                    break

    if not updated.get("destination_place_id"):
        for key in ("destination", "destination_label"):
            raw = updated.get(key)
            if raw:
                place = resolve_place(str(raw))
                if place:
                    updated["destination_place_id"] = place.id
                    updated["destination_label"] = place_label(place)
                    break

    if str(updated.get("origin_place_id", "")).upper() == "HUB_EU":
        updated["use_european_hubs"] = True

    if not updated.get("mode"):
        updated["mode"] = "fixed_trip"

    if updated.get("return_date") and updated.get("departure_date"):
        try:
            dep = date.fromisoformat(str(updated["departure_date"])[:10])
            ret = date.fromisoformat(str(updated["return_date"])[:10])
            updated.setdefault("trip_days", max(1, (ret - dep).days))
        except ValueError:
            pass

    updated.setdefault("flexible_departure_in_range", False)

    updated.setdefault("flexibility_days", 0)
    updated.setdefault("use_return_date", False)
    updated.setdefault("flexible_top_n", 3)

    if (
        updated.get("mode") == "date_range"
        and updated.get("date_from")
        and updated.get("date_to")
        and updated.get("flexible_departure_in_range")
    ):
        try:
            dep = date.fromisoformat(str(updated["date_from"])[:10])
            ret = date.fromisoformat(str(updated["date_to"])[:10])
            if ret > dep:
                updated["trip_days"] = (ret - dep).days
        except ValueError:
            pass
    elif (
        updated.get("mode") == "date_range"
        and updated.get("date_from")
        and updated.get("date_to")
        and not updated.get("flexible_departure_in_range")
    ):
        try:
            dep = date.fromisoformat(str(updated["date_from"])[:10])
            ret = date.fromisoformat(str(updated["date_to"])[:10])
            if ret > dep:
                updated["trip_days"] = (ret - dep).days
        except ValueError:
            pass
        updated["use_return_date"] = True

    updated.setdefault("trip_days", 5)
    updated.setdefault("target_country_ids", [])
    updated.setdefault("destination_scope", "anywhere")
    updated.setdefault("alliance", "any")
    updated.setdefault("prefer_thy", False)
    updated.setdefault("currency", "TRY")

    return updated


def _persist_if_changed(path: Path, raw: dict, saved: SavedSearch) -> None:
    checks = {
        "origin_place_id": saved.origin_place_id,
        "trip_days": saved.trip_days,
        "flexible_departure_in_range": saved.flexible_departure_in_range,
        "use_european_hubs": saved.use_european_hubs,
        "mode": saved.mode.value,
    }
    if any(raw.get(key) != value for key, value in checks.items()):
        path.write_text(saved.model_dump_json(indent=2), encoding="utf-8")


def save_quick_search(payload: ExploreSearchRequest) -> SavedSearch:
    ensure_data_dirs()
    now = _now_iso()
    path = SEARCHES_DIR / f"{QUICK_SEARCH_ID}.json"
    existing = load_search(QUICK_SEARCH_ID)
    created = existing.created_at if existing else now
    saved = SavedSearch(id=QUICK_SEARCH_ID, created_at=created, updated_at=now, **payload.model_dump())
    path.write_text(saved.model_dump_json(indent=2), encoding="utf-8")
    return saved


def load_search(search_id: str) -> SavedSearch | None:
    path = SEARCHES_DIR / f"{search_id}.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    migrated = migrate_legacy_search_data(raw)
    try:
        saved = SavedSearch.model_validate(migrated)
    except ValidationError:
        return None
    _persist_if_changed(path, raw, saved)
    return saved


def delete_results(search_id: str) -> int:
    ensure_data_dirs()
    removed = 0
    for path in RESULTS_DIR.glob(f"{search_id}_*.json"):
        path.unlink(missing_ok=True)
        removed += 1
    return removed


def delete_search(search_id: str) -> bool:
    path = SEARCHES_DIR / f"{search_id}.json"
    if not path.exists():
        return False
    path.unlink()
    delete_results(search_id)
    return True


def save_result(result: SearchRunResult) -> Path:
    ensure_data_dirs()
    filename = f"{result.search_id}_{result.source}_{result.scraped_at.replace(':', '-')}.json"
    path = RESULTS_DIR / filename
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return path


def list_results(search_id: str | None = None) -> list[SearchRunResult]:
    ensure_data_dirs()
    results: list[SearchRunResult] = []
    for path in sorted(RESULTS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            result = SearchRunResult.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if search_id and result.search_id != search_id:
            continue
        results.append(result)
    return results


def load_latest_result(search_id: str) -> SearchRunResult | None:
    results = list_results(search_id)
    return results[0] if results else None
