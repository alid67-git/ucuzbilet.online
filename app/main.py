from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pydantic import ValidationError

from app.flags import country_flag
from app.offer_display import format_miles, route_display
from app.regions import country_labels, load_continents, scope_label
from app.models import AllianceFilter, DestinationScope, ExploreMode, ExploreSearchRequest
from app.version import APP_VERSION, BETA_BUILD
from app.places import place_children, place_label, resolve_place, search_places
from app.runner import run_search
from app.storage import (
    delete_search,
    ensure_data_dirs,
    list_results,
    list_broken_searches,
    list_searches,
    load_search,
    save_result,
    save_search,
    save_quick_search,
    update_search,
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))
templates.env.filters["flag"] = country_flag
templates.env.filters["scope_label"] = scope_label
templates.env.filters["country_labels"] = country_labels
templates.env.filters["route_display"] = route_display
templates.env.filters["format_miles"] = format_miles

app = FastAPI(title="UcuzBilet Avcisi", version=APP_VERSION)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
templates.env.globals["app_version"] = APP_VERSION
templates.env.globals["beta_build"] = BETA_BUILD
templates.env.globals["beta_label"] = f"beta.{BETA_BUILD}"


def _default_dates() -> tuple[str, str, str]:
    today = date.today()
    return today.isoformat(), (today + timedelta(days=5)).isoformat(), (today + timedelta(days=30)).isoformat()


def _form_context(search=None) -> dict:
    today, default_return, default_range_end = _default_dates()
    return {
        "search": search,
        "today": today,
        "default_return": default_return,
        "default_range_end": default_range_end,
    }


def _place_payload(place) -> dict:
    item = {
        "id": place.id,
        "type": place.type,
        "label": place_label(place),
        "country": place.country,
        "city": place.city,
    }
    children = place_children(place)
    if children:
        item["children"] = [_place_payload(child) for child in children]
    return item


@app.on_event("startup")
def on_startup() -> None:
    ensure_data_dirs()


@app.get("/api/places/search")
async def api_search_places(q: str = Query("", min_length=0), limit: int = Query(20, ge=1, le=50)):
    places = search_places(q, limit=limit)
    return JSONResponse([_place_payload(place) for place in places])


@app.get("/api/places/resolve")
async def api_resolve_place(q: str = Query(..., min_length=1)):
    place = resolve_place(q)
    if not place:
        raise HTTPException(status_code=404, detail="Yer bulunamadi.")
    return JSONResponse({"id": place.id, "label": place_label(place), "type": place.type})


@app.get("/api/regions")
async def api_regions():
    return JSONResponse(load_continents())


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    searches = list_searches()
    broken_searches = list_broken_searches()
    today, _, _ = _default_dates()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"searches": searches, "broken_searches": broken_searches, "today": today},
    )


@app.get("/search", response_class=HTMLResponse)
async def search_form(request: Request):
    quick = load_search("quick")
    ctx = _form_context(quick)
    ctx.update(
        {
            "request": request,
            "action": "/searches",
            "run_action": "/search/run",
            "title": "Ucuz bilet ara",
            "is_quick_form": True,
        }
    )
    return templates.TemplateResponse(request, "form.html", ctx)


@app.get("/searches/new", response_class=HTMLResponse)
async def new_search_form(request: Request):
    return RedirectResponse(url="/search", status_code=303)


@app.get("/searches/{search_id}/edit", response_class=HTMLResponse)
async def edit_search_form(request: Request, search_id: str):
    if search_id == "quick":
        return RedirectResponse(url="/search", status_code=303)
    search = load_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Arama bulunamadi.")
    ctx = _form_context(search)
    ctx.update(
        {
            "request": request,
            "action": f"/searches/{search_id}",
            "run_action": "/search/run",
            "title": "Aramayi duzenle",
            "is_quick_form": False,
        }
    )
    return templates.TemplateResponse(request, "form.html", ctx)


@app.get("/searches/{search_id}", response_class=HTMLResponse)
async def search_detail(request: Request, search_id: str):
    search = load_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Arama bulunamadi.")
    results = list_results(search_id)
    latest_results = results[:1] if results else []
    return templates.TemplateResponse(
        request,
        "detail.html",
        {"search": search, "results": latest_results, "is_quick": search_id == "quick"},
    )


def _parse_date_field(raw: str, label: str) -> date | None:
    if not raw or not raw.strip():
        return None
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Gecersiz {label} tarihi.") from exc


def _parse_search_form(
    name: str,
    origin_place_id: str,
    destination_place_id: str,
    use_european_hubs: str | None,
    mode: str,
    date_from: str,
    date_to: str,
    trip_days: int,
    use_return_date: str | None,
    flexible_search: str | None,
    flexibility_days: int,
    destination_scope: str,
    target_countries: list[str],
    alliance: str,
    prefer_thy: str | None,
    max_stops: str,
    adults: int,
    children: int,
    max_price: str,
    cabin_class: str,
) -> ExploreSearchRequest:
    hub = use_european_hubs == "on" or mode == "hub_to_country"
    if mode == "hub_to_country":
        mode = "fixed_trip"

    dest_id = destination_place_id.strip() or None
    dest = resolve_place(dest_id) if dest_id else None
    if dest_id and not dest:
        raise HTTPException(status_code=400, detail="Gecerli bir varis noktasi secin.")

    origin_id = origin_place_id.strip()
    origin = resolve_place(origin_id) if origin_id and not hub else None
    if not hub:
        if not origin:
            raise HTTPException(status_code=400, detail="Gecerli bir kalkis noktasi secin.")
        if dest and origin:
            if origin.id.upper() == dest.id.upper():
                raise HTTPException(status_code=400, detail="Kalkis ve varis ayni olamaz.")
            if (
                origin.country_code == dest.country_code
                and dest.type in ("country", "city")
                and origin.type in ("country", "city", "airport")
            ):
                raise HTTPException(
                    status_code=400,
                    detail="Varis, kalkisla ayni ulke/sehir olamaz. Ornek: Istanbul → New York.",
                )

    parsed_from = _parse_date_field(date_from, "gidis")
    parsed_to = _parse_date_field(date_to, "donus") if date_to.strip() else None
    parsed_max_stops = int(max_stops) if max_stops.strip() else None
    parsed_max_price = int(max_price) if max_price.strip() else None

    use_return = use_return_date == "on"
    one_way_trip = not use_return
    flex = flexible_search == "on"
    explore_mode = ExploreMode(mode)

    if explore_mode != ExploreMode.FLEXIBLE:
        if use_return:
            explore_mode = ExploreMode.DATE_RANGE
        else:
            explore_mode = ExploreMode.FIXED_TRIP

    if explore_mode != ExploreMode.FLEXIBLE and not parsed_from:
        raise HTTPException(status_code=400, detail="Gidis tarihi zorunludur.")

    try:
        return ExploreSearchRequest(
            name=name.strip(),
            origin_place_id=origin.id if origin else "HUB_EU",
            origin_label=place_label(origin) if origin else "",
            destination_place_id=dest.id if dest else None,
            destination_label=place_label(dest) if dest else "",
            use_european_hubs=hub,
            mode=explore_mode,
            departure_date=parsed_from,
            date_from=parsed_from,
            date_to=parsed_to if use_return else None,
            trip_days=trip_days,
            use_return_date=use_return,
            one_way=one_way_trip,
            flexible_departure_in_range=flex,
            flexibility_days=max(0, flexibility_days) if flex else 0,
            flexible_top_n=3,
            destination_scope=DestinationScope(destination_scope),
            target_country_ids=[c for c in target_countries if c.strip()],
            alliance=AllianceFilter(alliance),
            prefer_thy=prefer_thy == "on",
            max_stops=parsed_max_stops,
            direct_only=False,
            adults=adults,
            children=children,
            max_price=parsed_max_price,
            cabin_class=cabin_class,  # type: ignore[arg-type]
            headless=True,
        )
    except ValidationError as exc:
        msg = exc.errors()[0].get("msg", "Gecersiz arama kriterleri.")
        raise HTTPException(status_code=400, detail=str(msg)) from exc


async def _run_search_and_save(saved) -> None:
    results = await run_search(saved)
    for result in results:
        save_result(result)


@app.post("/search/run")
async def quick_search_run(
    name: str = Form(""),
    origin_place_id: str = Form(""),
    destination_place_id: str = Form(""),
    use_european_hubs: str | None = Form(None),
    mode: str = Form("fixed_trip"),
    date_from: str = Form(""),
    date_to: str = Form(""),
    trip_days: int = Form(5),
    use_return_date: str | None = Form(None),
    flexible_search: str | None = Form(None),
    flexibility_days: int = Form(3),
    destination_scope: str = Form("anywhere"),
    target_countries: list[str] = Form(default=[]),
    alliance: str = Form("any"),
    prefer_thy: str | None = Form(None),
    max_stops: str = Form(""),
    adults: int = Form(1),
    children: int = Form(0),
    max_price: str = Form(""),
    cabin_class: str = Form("economy"),
):
    payload = _parse_search_form(
        name or f"Hizli arama {date.today().isoformat()}",
        origin_place_id,
        destination_place_id,
        use_european_hubs,
        mode,
        date_from,
        date_to,
        trip_days,
        use_return_date,
        flexible_search,
        flexibility_days,
        destination_scope,
        target_countries,
        alliance,
        prefer_thy,
        max_stops,
        adults,
        children,
        max_price,
        cabin_class,
    )
    saved = save_quick_search(payload)
    await _run_search_and_save(saved)
    return RedirectResponse(url="/searches/quick", status_code=303)


@app.post("/searches")
async def create_search(
    name: str = Form(""),
    origin_place_id: str = Form(""),
    destination_place_id: str = Form(""),
    use_european_hubs: str | None = Form(None),
    mode: str = Form("fixed_trip"),
    date_from: str = Form(""),
    date_to: str = Form(""),
    trip_days: int = Form(5),
    use_return_date: str | None = Form(None),
    flexible_search: str | None = Form(None),
    flexibility_days: int = Form(3),
    destination_scope: str = Form("anywhere"),
    target_countries: list[str] = Form(default=[]),
    alliance: str = Form("any"),
    prefer_thy: str | None = Form(None),
    max_stops: str = Form(""),
    adults: int = Form(1),
    children: int = Form(0),
    max_price: str = Form(""),
    cabin_class: str = Form("economy"),
):
    payload = _parse_search_form(
        name.strip() or f"Arama {date.today().isoformat()}",
        origin_place_id,
        destination_place_id,
        use_european_hubs,
        mode,
        date_from,
        date_to,
        trip_days,
        use_return_date,
        flexible_search,
        flexibility_days,
        destination_scope,
        target_countries,
        alliance,
        prefer_thy,
        max_stops,
        adults,
        children,
        max_price,
        cabin_class,
    )
    saved = save_search(payload)
    return RedirectResponse(url=f"/searches/{saved.id}", status_code=303)


@app.post("/searches/from-quick")
async def save_from_quick(name: str = Form(...)):
    quick = load_search("quick")
    if not quick:
        raise HTTPException(status_code=404, detail="Hizli arama bulunamadi.")
    payload = ExploreSearchRequest.model_validate(
        {**quick.model_dump(exclude={"id", "created_at", "updated_at"}), "name": name.strip()}
    )
    saved = save_search(payload)
    return RedirectResponse(url=f"/searches/{saved.id}", status_code=303)


@app.post("/searches/{search_id}")
async def update_search_route(
    search_id: str,
    name: str = Form(...),
    origin_place_id: str = Form(""),
    destination_place_id: str = Form(""),
    use_european_hubs: str | None = Form(None),
    mode: str = Form("fixed_trip"),
    date_from: str = Form(""),
    date_to: str = Form(""),
    trip_days: int = Form(5),
    use_return_date: str | None = Form(None),
    flexible_search: str | None = Form(None),
    flexibility_days: int = Form(3),
    destination_scope: str = Form("anywhere"),
    target_countries: list[str] = Form(default=[]),
    alliance: str = Form("any"),
    prefer_thy: str | None = Form(None),
    max_stops: str = Form(""),
    adults: int = Form(1),
    children: int = Form(0),
    max_price: str = Form(""),
    cabin_class: str = Form("economy"),
):
    payload = _parse_search_form(
        name,
        origin_place_id,
        destination_place_id,
        use_european_hubs,
        mode,
        date_from,
        date_to,
        trip_days,
        use_return_date,
        flexible_search,
        flexibility_days,
        destination_scope,
        target_countries,
        alliance,
        prefer_thy,
        max_stops,
        adults,
        children,
        max_price,
        cabin_class,
    )
    updated = update_search(search_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Arama bulunamadi.")
    return RedirectResponse(url=f"/searches/{search_id}", status_code=303)


@app.post("/searches/{search_id}/run")
async def run_search_route(search_id: str):
    search = load_search(search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Arama bulunamadi.")

    results = await run_search(search)
    for result in results:
        save_result(result)

    return RedirectResponse(url=f"/searches/{search_id}", status_code=303)


@app.post("/searches/{search_id}/delete")
async def delete_search_route(search_id: str):
    if not delete_search(search_id):
        raise HTTPException(status_code=404, detail="Arama bulunamadi.")
    return RedirectResponse(url="/", status_code=303)
