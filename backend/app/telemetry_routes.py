import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .ai.gateway import ProviderError, cipher
from .auth import current_user, require_admin
from .city import sensors
from .city_routes import require_city
from .db import Store, db, engine, now
from .operations import require_feature
from .telemetry import SCHEMES, city_readings, config_check, coverage_plan, transit_positions

router = APIRouter(prefix="/telemetry", tags=["Live telemetry"])


class FeedForm(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    city_id: str = Field(pattern=r"^[a-z0-9-]{1,48}$")
    kind: str = Field(max_length=20)
    url: str = Field(min_length=8, max_length=500)
    topic: str = Field(default="", max_length=180)
    username: str = Field(default="", max_length=100)
    secret: str = Field(default="", max_length=2048)
    interval: int = Field(default=60, ge=10, le=3600)
    enabled: bool = True


def public_feed(row):
    return {key: value for key, value in row.items() if key != "credential"} | {
        "hasCredential": bool(row.get("credential"))
    }


@router.get("/feeds")
def feeds(store: Store = Depends(db), user=Depends(require_admin)):
    return [public_feed(row) for row in store.list(user["scope"], "feed")]


def save_feed(store, scope, form, existing=None):
    require_feature(store, scope, "telemetry")
    require_city(store, scope, form.city_id)
    if form.kind not in SCHEMES:
        raise HTTPException(422, "Select a supported telemetry adapter.")
    try:
        config_check(form.kind, form.url, form.topic)
        encrypted = (
            cipher().encrypt(form.secret.encode()).decode()
            if form.secret
            else (existing.get("credential", "") if existing else "")
        )
    except (ValueError, ProviderError) as exc:
        raise HTTPException(422, str(exc)) from exc
    key = existing["id"] if existing else uuid4().hex
    row = {
        **form.model_dump(exclude={"secret"}),
        "id": key,
        "credential": encrypted,
        "next_poll": 0,
        "status": "pending" if form.enabled else "disabled",
        "error": "",
        "last_success": None,
        "readings": 0,
        "vehicles": 0,
    }
    store.put(scope, "feed", key, row)
    store.session.commit()
    return public_feed(row)


@router.post("/feeds", status_code=201)
def add_feed(form: FeedForm, store: Store = Depends(db), user=Depends(require_admin)):
    return save_feed(store, user["scope"], form)


@router.post("/demo-feed", status_code=201)
def activate_demo(store: Store = Depends(db), user=Depends(require_admin)):
    scope, key = user["scope"], "demo-debrecen"
    require_feature(store, scope, "telemetry")
    row = {
        "id": key,
        "name": "Simulated telemetry",
        "city_id": "debrecen",
        "kind": "simulated",
        "enabled": True,
        "interval": 15,
        "next_poll": 0,
        "status": "pending",
        "url": "",
        "error": "",
        "readings": 0,
        "vehicles": 0,
    }
    store.put(scope, "feed", key, row)
    store.session.commit()
    return public_feed(row)


@router.delete("/feeds/{feed_id}")
def pause_feed(feed_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    row = store.get(scope, "feed", feed_id, lock=True)
    if not row:
        raise HTTPException(404, "Telemetry feed not found.")
    store.put(scope, "feed", feed_id, {**row, "enabled": False, "status": "disabled"})
    store.session.commit()
    return {"status": "disabled"}


@router.put("/feeds/{feed_id}")
def change_feed(feed_id: str, form: FeedForm, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    existing = store.get(scope, "feed", feed_id, lock=True)
    if not existing:
        raise HTTPException(404, "Telemetry feed not found.")
    if any(existing[key] != getattr(form, key) for key in ("url", "username", "kind")):
        existing = {**existing, "credential": ""}
    return save_feed(store, scope, form, existing)


@router.post("/feeds/{feed_id}/refresh", status_code=202)
def queue_feed(feed_id: str, store: Store = Depends(db), user=Depends(require_admin)):
    scope = user["scope"]
    row = store.get(scope, "feed", feed_id, lock=True)
    if not row or not row["enabled"]:
        raise HTTPException(404, "Enabled telemetry feed not found.")
    store.put(scope, "feed", feed_id, {**row, "next_poll": 0, "status": "pending"})
    store.session.commit()
    return {"status": "pending"}


@router.get("/coverage")
def coverage(city_id: str = "debrecen", count: int = 5, store: Store = Depends(db), user=Depends(current_user)):
    if not 1 <= count <= 12:
        raise HTTPException(422, "Choose between 1 and 12 sensor sites.")
    scope = user["scope"]
    require_feature(store, scope, "telemetry")
    city = require_city(store, scope, city_id)
    active = [row for row in sensors(city, city_readings(store, scope, city_id)) if row["online"]]
    return coverage_plan(city, active, count)


@router.get("/vehicles")
def vehicles(city_id: str = "debrecen", store: Store = Depends(db), user=Depends(current_user)):
    require_city(store, user["scope"], city_id)
    return transit_positions(store, user["scope"], city_id)


def latest(scope, city_id):
    with Session(engine) as session:
        return Store(session).list(scope, "telemetry-event", 100, city_id=city_id)


@router.get("/events")
def live_events(
    request: Request, city_id: str = "debrecen", store: Store = Depends(db), user=Depends(current_user)
):
    scope = user["scope"]
    require_feature(store, scope, "telemetry")
    require_city(store, scope, city_id)
    started = now().isoformat()

    async def stream():
        cursor = (started, "")
        ticks = 0
        while not await request.is_disconnected() and ticks < 900:
            rows = await asyncio.to_thread(latest, scope, city_id)
            for event in sorted(rows, key=lambda row: (row["time"], row["id"])):
                mark = event["time"], event["id"]
                if mark > cursor:
                    cursor = mark
                    yield f"id: {event['id']}\ndata: {json.dumps(event)}\n\n"
            if ticks % 7 == 0:
                yield ": keepalive\n\n"
            ticks += 1
            await asyncio.sleep(2)

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
