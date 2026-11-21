from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .auth import current_user, require_admin
from .city import LAYERS, cities, city_for, city_layers, sensors
from .db import Store, db
from .geospatial import supports_network
from .telemetry import city_readings
from .workspace import coordinate, ingest, notifications

router = APIRouter(tags=["Cities"])


def require_city(store, scope, city_id):
    city = city_for(store, scope, city_id)
    if city is None:
        raise HTTPException(404, "City not found.")
    return city


def public_city(city):
    return {
        key: city[key]
        for key in ("id", "name", "country", "center", "zoom", "timezone", "source", "origin", "kpis")
    }


class CityForm(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]{1,48}$")
    name: str = Field(min_length=2, max_length=80)
    country: str = Field(min_length=2, max_length=80)
    center: list[float] = Field(min_length=2, max_length=2)
    zoom: float = Field(default=12, ge=2, le=20)
    timezone: str = Field(default="UTC", max_length=80)
    nodes: dict[str, list[float]] = Field(default_factory=dict, max_length=3000)
    edges: list[tuple[str, str, float, float, list[list[float]]]] = Field(default_factory=list, max_length=4000)
    demand: list[tuple[str, str, float]] = Field(default_factory=list, max_length=1000)


class SourceForm(BaseModel):
    city_id: str = Field(pattern=r"^[a-z0-9-]{1,48}$")
    name: str = Field(min_length=2, max_length=100)
    layer: str
    format: str
    content: Any


@router.get("/cities")
def list_cities(store: Store = Depends(db), user=Depends(current_user)):
    return [public_city(city) for city in cities(store, user["scope"])]


@router.post("/cities", status_code=201)
def add_city(form: CityForm, store: Store = Depends(db), user=Depends(require_admin)):
    import math
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    if city_for(store, user["scope"], form.id):
        raise HTTPException(409, "A city with this ID already exists.")
    try:
        ZoneInfo(form.timezone)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise HTTPException(422, "Use a valid IANA time zone.") from exc
    if not coordinate(form.center) or not all(coordinate(value) for value in form.nodes.values()):
        raise HTTPException(422, "City coordinates are invalid.")
    if any(
        a not in form.nodes
        or b not in form.nodes
        or not 0 < mins <= 500
        or not 0 < cap <= 1_000_000
        or not all(coordinate(p) for p in shape)
        for a, b, mins, cap, shape in form.edges
    ):
        raise HTTPException(422, "Route graph contains invalid edges.")
    if any(
        a not in form.nodes or b not in form.nodes or not math.isfinite(val) or not 0 < val <= 1_000_000
        for a, b, val in form.demand
    ):
        raise HTTPException(422, "Demand pairs are invalid.")
    if not supports_network(form.edges, form.demand):
        raise HTTPException(422, "Demand pairs must be connected by the road graph.")
    data = {
        **form.model_dump(mode="json"),
        "origin": form.center,
        "source": "Workspace scenario data · modeled",
        "districts": [],
        "sensors": [],
        "incidents": [],
        "transit": [],
        "kpis": {},
    }
    store.insert(user["scope"], "city", form.id, data)
    store.session.commit()
    return public_city(data)


@router.get("/cities/{city_id}")
def city_detail(city_id: str, store: Store = Depends(db), user=Depends(current_user)):
    return public_city(require_city(store, user["scope"], city_id))


@router.get("/cities/{city_id}/layers")
def layers(city_id: str, store: Store = Depends(db), user=Depends(current_user)):
    city = require_city(store, user["scope"], city_id)
    return {**city_layers(city, store, user["scope"]), "layers": LAYERS}


@router.get("/sensors")
def list_sensors(city_id: str = "debrecen", store: Store = Depends(db), user=Depends(current_user)):
    scope = user["scope"]
    return sensors(require_city(store, scope, city_id), city_readings(store, scope, city_id))


@router.get("/incidents")
def list_incidents(city_id: str = "debrecen", store: Store = Depends(db), user=Depends(current_user)):
    return require_city(store, user["scope"], city_id)["incidents"]


@router.get("/mobility")
def mobility(city_id: str = "debrecen", store: Store = Depends(db), user=Depends(current_user)):
    scope = user["scope"]
    routes = require_city(store, scope, city_id)["transit"]
    return [
        *routes,
        *(route for source in store.list(scope, "source", city_id=city_id) for route in source.get("routes", [])),
    ]


@router.get("/notifications")
def list_notifications(city_id: str = "debrecen", store: Store = Depends(db), user=Depends(current_user)):
    scope = user["scope"]
    if not user["preferences"]["notifications"]:
        return []
    read_at = (store.get(scope, "notice-read", user["id"]) or {}).get("read_at", "")
    return [
        {**row, "unread": not read_at or ("T" in row["time"] and row["time"] > read_at)}
        for row in notifications(store, scope, require_city(store, scope, city_id))
    ]


@router.get("/data-sources")
def data_sources(store: Store = Depends(db), user=Depends(current_user)):
    return [source_summary(row) for row in store.list(user["scope"], "source")]


@router.post("/data-sources", status_code=201)
def add_source(form: SourceForm, store: Store = Depends(db), user=Depends(require_admin)):
    require_city(store, user["scope"], form.city_id)
    row = ingest(store, user["scope"], form.city_id, form.name, form.layer, form.format, form.content)
    return source_summary(row)


def source_summary(row):
    return {key: val for key, val in row.items() if key not in {"features", "routes"}} | {
        "feature_count": len(row["features"]),
        "route_count": len(row.get("routes", [])),
    }


@router.delete("/data-sources/{source_id}", status_code=204)
def delete_source(source_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    if not store.remove(scope, "source", source_id):
        raise HTTPException(404, "Data source not found.")
    store.remove_spatial(scope, source_id)
    store.session.commit()
    return Response(status_code=204)
