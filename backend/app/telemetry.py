"""Read and normalize approved telemetry sources into tenant-scoped readings."""

import json
import logging
import os
import re
import socket
import ssl
from datetime import UTC, datetime
from uuid import uuid4

from cryptography.fernet import InvalidToken
from google.transit import gtfs_realtime_pb2
from paho.mqtt import client as mqtt
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from websocket import create_connection

from .ai.gateway import cipher
from .db import Record, Store, engine, now
from .outbound import EndpointError, request_bytes, resolve

log = logging.getLogger("agentcity.telemetry")
KEY = re.compile(r"^[a-zA-Z0-9_.-]{1,54}$")
SCHEMES = {
    "rest": {"https", "http"},
    "gtfs-realtime": {"https", "http"},
    "websocket": {"wss", "ws"},
    "mqtt": {"mqtts", "mqtt"},
}
MAX_BYTES = 1_000_000


class Reading(BaseModel):
    sensor_id: str = Field(pattern=KEY.pattern)
    value: float | None = Field(allow_inf_nan=False)
    observed_at: datetime
    name: str = Field(default="", max_length=120)
    type: str = Field(default="Sensor", max_length=40)
    unit: str = Field(default="", max_length=24)
    coordinates: list[float] | None = None
    radius: int = Field(default=300, ge=25, le=10000)
    uptime: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("observed_at")
    @classmethod
    def utc_stamp(cls, value):
        if value.tzinfo is None:
            raise ValueError("A timezone offset is required.")
        return value.astimezone(UTC)

    @field_validator("coordinates")
    @classmethod
    def geographic(cls, value):
        if value is not None and (len(value) != 2 or not -180 <= value[0] <= 180 or not -85 <= value[1] <= 85):
            raise ValueError("Coordinates must be longitude and latitude.")
        return value


def config_check(kind, url, topic):
    parsed, _, _ = resolve(url, "TELEMETRY_ORIGINS", SCHEMES[kind])
    if kind == "mqtt" and (not topic or "+" in topic or "#" in topic or parsed.path not in {"", "/"}):
        raise EndpointError("Use a single MQTT topic and a broker URL without a path.")


def read_websocket(url, secret):
    parsed, address, port = resolve(url, "TELEMETRY_ORIGINS", SCHEMES["websocket"])
    with socket.create_connection((address, port), timeout=8) as raw:
        sock = (
            ssl.create_default_context().wrap_socket(raw, server_hostname=parsed.hostname)
            if parsed.scheme == "wss"
            else raw
        )
        connection = create_connection(
            url,
            socket=sock,
            timeout=8,
            header={"Authorization": "Bearer " + secret} if secret else None,
            redirect_limit=0,
        )
        try:
            content = connection.recv()
            data = content.encode() if isinstance(content, str) else content
            if len(data) > MAX_BYTES:
                raise EndpointError("The endpoint response exceeded the size limit.")
            return data
        finally:
            connection.close(timeout=1)


def read_mqtt(url, topic, username, secret):
    parsed, _, port = resolve(url, "TELEMETRY_ORIGINS", SCHEMES["mqtt"])
    from time import monotonic

    connection = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    received = []
    connection.on_connect = lambda client, *_: client.subscribe(topic, qos=1)
    connection.on_message = lambda _client, _data, msg: received.append(msg.payload[: MAX_BYTES + 1])
    if username:
        connection.username_pw_set(username, secret or None)
    if parsed.scheme == "mqtts":
        connection.tls_set_context(ssl.create_default_context())
    connection.connect_timeout = 5
    connection.connect(parsed.hostname, port, keepalive=10)
    deadline = monotonic() + 8
    try:
        while not received and monotonic() < deadline:
            connection.loop(timeout=0.25)
    finally:
        connection.disconnect()
    if not received or len(received[0]) > MAX_BYTES:
        raise EndpointError("No bounded MQTT message was received.")
    return received[0]


def decode(kind, raw):
    if kind != "gtfs-realtime":
        body = json.loads(raw)
        readings = body.get("readings", []) if isinstance(body, dict) else body
        if not isinstance(readings, list) or len(readings) > 1000:
            raise EndpointError("Provide an array of up to 1,000 readings.")
        return [Reading.model_validate(row) for row in readings], []
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(raw)
    if not feed.IsInitialized():
        raise EndpointError("The GTFS-Realtime feed is missing required fields.")
    stamp = datetime.fromtimestamp(feed.header.timestamp, UTC) if feed.header.timestamp else now()
    vehicles, delays = [], {}
    for item in list(feed.entity)[:1000]:
        if item.HasField("trip_update"):
            update = item.trip_update
            delays[update.trip.trip_id] = (
                update.delay
                if update.HasField("delay")
                else next(
                    (
                        stop.arrival.delay
                        for stop in update.stop_time_update
                        if stop.HasField("arrival") and stop.arrival.HasField("delay")
                    ),
                    0,
                )
            )
        if item.HasField("vehicle") and item.vehicle.HasField("position"):
            vehicle = item.vehicle
            point = vehicle.position
            if -180 <= point.longitude <= 180 and -85 <= point.latitude <= 85:
                vehicles.append(
                    {
                        "id": item.id[:80],
                        "trip": vehicle.trip.trip_id[:80],
                        "route": vehicle.trip.route_id[:80],
                        "coordinates": [point.longitude, point.latitude],
                        "observed_at": (
                            datetime.fromtimestamp(vehicle.timestamp, UTC) if vehicle.timestamp else stamp
                        ).isoformat(),
                    }
                )
    for vehicle in vehicles:
        vehicle["delay"] = delays.get(vehicle["trip"])
    present = {item["trip"] for item in vehicles}
    vehicles.extend(
        {
            "id": trip[:80],
            "trip": trip[:80],
            "route": "",
            "coordinates": None,
            "observed_at": stamp.isoformat(),
            "delay": delay,
        }
        for trip, delay in delays.items()
        if trip not in present
    )
    return [], vehicles


def fetch(source):
    kind = source["kind"]
    if kind == "simulated":
        from .city import DEBRECEN

        stamp = now()
        variation = ((stamp.minute % 5) - 2) * 0.035
        return [
            Reading(
                sensor_id=row["id"],
                value=round(row["reading"] * (1 + variation), 1),
                observed_at=stamp,
                name=row["name"],
                type=row["type"],
                unit=row["unit"],
                coordinates=row["coordinates"],
                radius=row["radius"],
                uptime=row.get("uptime"),
                confidence=row.get("confidence"),
            )
            for row in DEBRECEN["sensors"]
            if row["reading"] is not None
        ], []
    source_url = source["url"]
    secret = ""
    if source.get("credential"):
        try:
            secret = cipher().decrypt(source["credential"].encode()).decode()
        except InvalidToken as exc:
            raise EndpointError("The feed credential could not be opened.") from exc
    if kind == "websocket":
        raw = read_websocket(source_url, secret)
    elif kind == "mqtt":
        raw = read_mqtt(source_url, source["topic"], source["username"], secret)
    else:
        raw = request_bytes(
            "GET",
            source_url,
            "TELEMETRY_ORIGINS",
            headers={"Authorization": "Bearer " + secret} if secret else None,
            limit=MAX_BYTES,
        )
    return decode(kind, raw)


def commit_snapshot(store, scope, source, readings, vehicles):
    city = source["city_id"]
    updated = []
    for reading in readings:
        row = reading.model_dump(mode="json")
        key = f"{city}:{row['sensor_id']}"
        old = store.get(scope, "reading", key, lock=True) or {}
        simulated = source["kind"] == "simulated"
        if old and simulated and old["source"] != "Simulated":
            continue
        if old and not simulated and old["source"] == "Simulated":
            old = {}
        is_latest = row["observed_at"] >= old.get("observed_at", "")
        if is_latest and row["value"] is None and (not old or old.get("value") is not None):
            from .delivery import publish

            publish(store, scope, event="sensor.offline", city_id=city, title=reading.sensor_id + " is offline")
        history = {item["observed_at"]: item["value"] for item in old.get("history", [])}
        history[row["observed_at"]] = row["value"]
        series = [{"observed_at": stamp, "value": value} for stamp, value in sorted(history.items())[-100:]]
        latest = (
            {**row, "source": "Simulated" if simulated else source["name"], "source_id": source["id"]}
            if is_latest
            else old
        )
        store.put(
            scope,
            "reading",
            key,
            {**latest, "history": series, "city_id": city},
        )
        updated.append(row["sensor_id"])
    if source["kind"] == "gtfs-realtime":
        store.put(scope, "vehicle-snapshot", source["id"], {"city_id": city, "vehicles": vehicles})
    if updated or vehicles:
        key = uuid4().hex
        store.insert(
            scope,
            "telemetry-event",
            key,
            {
                "id": key,
                "city_id": city,
                "source_id": source["id"],
                "time": now().isoformat(),
                "sensors": sorted(set(updated)),
                "vehicles": len(vehicles),
            },
        )
    return {"readings": len(readings), "vehicles": len(vehicles)}


def refresh(scope, source_id):
    with Session(engine) as session:
        source = Store(session).get(scope, "feed", source_id)
    if not source or not source["enabled"]:
        return
    try:
        readings, vehicles = fetch(source)
        with Session(engine) as session, session.begin():
            store = Store(session)
            saved = store.get(scope, "feed", source_id, lock=True)
            if not saved or saved["url"] != source["url"] or not saved["enabled"]:
                return
            stats = commit_snapshot(store, scope, source, readings, vehicles)
            store.put(
                scope,
                "feed",
                source_id,
                {**saved, "status": "online", "last_success": now().isoformat(), "error": "", **stats},
            )
    except Exception as error:
        log.warning("Feed refresh failed scope=%s source=%s type=%s", scope, source_id, type(error).__name__)
        with Session(engine) as session, session.begin():
            store = Store(session)
            saved = store.get(scope, "feed", source_id, lock=True)
            if saved:
                if saved["status"] != "error":
                    from .delivery import publish

                    publish(store, scope, event="feed.unavailable", city_id=saved["city_id"], title=saved["name"])
                store.put(
                    scope,
                    "feed",
                    source_id,
                    {
                        **saved,
                        "status": "error",
                        "error": "The feed could not be refreshed. Check its endpoint, credentials, and format.",
                    },
                )


def scheduled_refresh():
    with Session(engine) as session, session.begin():
        stamp = now().timestamp()
        elapsed = Record.payload["next_poll"].as_float()
        query = select(Record).where(
            Record.kind == "feed",
            Record.payload["enabled"].as_boolean().is_(True),
            or_(elapsed.is_(None), elapsed <= stamp),
        )
        if not os.getenv("TELEMETRY_ORIGINS"):
            query = query.where(Record.payload["kind"].as_string() == "simulated")
        row = session.scalar(query.order_by(elapsed, Record.key).limit(1).with_for_update(skip_locked=True))
        if row is None:
            return
        scope, key = row.scope, row.key
        row.payload = {**row.payload, "next_poll": stamp + max(10, row.payload["interval"])}
    refresh(scope, key)


def city_readings(store, scope, city):
    return store.list(scope, "reading", 1000, city_id=city)


def transit_positions(store, scope, city):
    since = now().timestamp() - 900
    return [
        {**vehicle, "stale": datetime.fromisoformat(vehicle["observed_at"]).timestamp() < since}
        for row in store.list(scope, "vehicle-snapshot", city_id=city)
        for vehicle in row["vehicles"]
    ]


def coverage_plan(city, online, count):
    from .simulation.engine import distance

    demand = {}
    for a, b, volume in city["demand"]:
        demand[a] = demand.get(a, 0) + volume
        demand[b] = demand.get(b, 0) + volume
    sites = city["nodes"]
    uncovered = {
        key
        for key, point in sites.items()
        if not any(
            distance(point, sensor["coordinates"]) <= sensor["radius"]
            for sensor in online
            if sensor["coordinates"]
        )
    }
    remaining = set(sites)
    plan = []
    neighbors = {
        key: {node for node in uncovered if distance(point, sites[node]) <= 450} for key, point in sites.items()
    }
    while uncovered and remaining and len(plan) < count:
        best = min(
            remaining,
            key=lambda key, needed=uncovered: (
                -sum(demand.get(node, 50) for node in neighbors[key] & needed),
                key,
            ),
        )
        gained = neighbors[best] & uncovered
        if not gained:
            break
        plan.append(
            {
                "id": best,
                "name": best,
                "coordinates": sites[best],
                "radius": 450,
                "covered_nodes": len(gained),
                "demand_weight": sum(demand.get(key, 50) for key in gained),
            }
        )
        uncovered -= gained
        remaining.remove(best)
    return {"candidates": plan, "uncovered_nodes": len(uncovered), "mode": "Modeled planning estimate"}
