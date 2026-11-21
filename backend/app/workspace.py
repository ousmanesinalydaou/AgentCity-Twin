import csv
import io
import math
import os
from collections import defaultdict
from uuid import uuid4

from fastapi import HTTPException

from .ai.gateway import configured_providers
from .auth import person
from .city import LAYERS
from .gtfs_schedule import MAX_FEATURES, import_schedule


def providers_for(store, scope, demo=False):
    configured = configured_providers()
    if demo:
        provider_ids = {item.strip() for item in os.getenv("DEMO_LOCAL_PROVIDER", "").split(",")}
        return [config for config in configured if config["local"] and config["id"] in provider_ids]
    benchmarks = {row["provider"]: row for row in store.list(scope, "benchmark")}
    return [
        {**config, "benchmark": benchmarks.get(config["id"], {})}
        for config in [*configured, *store.list(scope, "provider")]
    ]


def members(store, scope):
    return [person(store, row["id"]) for row in store.list(scope, "member")]


def notifications(store, scope, city):
    from .city import sensors
    from .telemetry import city_readings

    rows = [
        {"id": "incident-" + item["id"], "type": "incident", "text": item["name"], "time": item["age"]}
        for item in city["incidents"]
    ]
    rows.extend(
        {
            "id": "offline-" + item["id"],
            "type": "sensor",
            "text": item["name"] + " is offline",
            "time": item.get("observed_at", ""),
        }
        for item in sensors(city, city_readings(store, scope, city["id"]))
        if not item["online"]
    )
    for run in store.list(scope, "run", 12):
        if run["city_id"] != city["id"]:
            continue
        if run["status"] in {"completed", "failed"}:
            rows.append({"id": run["id"], "type": run["status"], "text": run["title"], "time": run["created_at"]})
        for entry in run["events"]:
            if entry["stage"] in {"fallback", "warning"}:
                rows.append(
                    {
                        "id": f"{run['id']}-{entry['seq']}",
                        "type": entry["stage"],
                        "text": entry["text"],
                        "time": entry["time"],
                    }
                )
    persisted = store.list(scope, "notice", 30, city_id=city["id"])
    return [*persisted, *rows]


def coordinate(value):
    return (
        isinstance(value, list)
        and len(value) == 2
        and all(type(item) in {int, float} and math.isfinite(item) for item in value)
        and -180 <= value[0] <= 180
        and -85 <= value[1] <= 85
    )


def valid_geometry(geometry):
    if not isinstance(geometry, dict):
        return False
    kind, coords = geometry.get("type"), geometry.get("coordinates")
    if kind == "Point":
        return coordinate(coords)
    if not isinstance(coords, list):
        return False
    if kind == "LineString":
        return 2 <= len(coords) <= 5000 and all(coordinate(p) for p in coords)
    if kind == "Polygon":
        return 1 <= len(coords) <= 20 and all(
            isinstance(ring, list)
            and 4 <= len(ring) <= 5000
            and ring[0] == ring[-1]
            and all(coordinate(p) for p in ring)
            for ring in coords
        )
    return False


def csv_features(content, gtfs):
    try:
        rows = csv.DictReader(io.StringIO(content))
        if gtfs:
            routes = defaultdict(list)
            for row in rows:
                routes[row["shape_id"]].append(
                    (int(row["shape_pt_sequence"]), [float(row["shape_pt_lon"]), float(row["shape_pt_lat"])])
                )
            return [
                {
                    "geometry": {"type": "LineString", "coordinates": [p for _, p in sorted(points)]},
                    "properties": {"name": name},
                }
                for name, points in routes.items()
            ]
        return [
            {
                "geometry": {"type": "Point", "coordinates": [float(row["longitude"]), float(row["latitude"])]},
                "properties": {"name": row["name"]},
            }
            for row in rows
        ]
    except (ValueError, KeyError, TypeError, csv.Error) as exc:
        raise HTTPException(422, "CSV columns or coordinates are invalid.") from exc


def ingest(store, scope, city_id, name, layer, format, content):
    if layer not in LAYERS:
        raise HTTPException(422, "Select an available map layer.")
    routes = []
    if format == "gtfs-zip" and isinstance(content, str):
        layer = "Transit"
        try:
            features, routes = import_schedule(content)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    elif format in {"csv", "gtfs"} and isinstance(content, str):
        features = csv_features(content, format == "gtfs")
    elif format == "geojson" and isinstance(content, dict) and content.get("type") == "FeatureCollection":
        features = content.get("features")
    elif format == "json" and isinstance(content, list):
        if any(not isinstance(row, dict) for row in content):
            raise HTTPException(422, "JSON expects an array of named points.")
        features = [
            {
                "geometry": {"type": "Point", "coordinates": row.get("coordinates")},
                "properties": {"name": row.get("name", "")},
            }
            for row in content
        ]
    else:
        raise HTTPException(422, "Upload a matching GeoJSON, JSON, CSV, or GTFS shapes file.")
    if not isinstance(features, list) or not 1 <= len(features) <= (MAX_FEATURES if routes else 1000):
        raise HTTPException(422, "A source must contain between 1 and 1000 features.")
    source_id = uuid4().hex
    clean = []
    for feature in features:
        if not isinstance(feature, dict) or not valid_geometry(feature.get("geometry")):
            raise HTTPException(422, "Use valid point, line, or polygon geometry.")
        properties = feature.get("properties")
        properties = properties if isinstance(properties, dict) else {}
        original = feature["geometry"]
        geometry = {"type": original["type"], "coordinates": original["coordinates"]}
        clean.append(
            {
                "type": "Feature",
                "geometry": geometry,
                "properties": {
                    "layer": layer,
                    "name": str(properties.get("name") or name)[:120],
                    "source": name,
                    "source_id": source_id,
                    "pressure": 40,
                    **{
                        key: properties[key]
                        for key in ("route_id", "stop_id", "color", "approximate")
                        if routes and key in properties
                    },
                },
            }
        )
        store.spatial(scope, city_id, source_id, geometry)
    source = {
        "id": source_id,
        "city_id": city_id,
        "name": name,
        "layer": layer,
        "format": format,
        "features": clean,
    }
    if routes:
        source["routes"] = [
            {**route, "id": source_id + ":" + route["route_id"], "source": name} for route in routes
        ]
    store.insert(scope, "source", source_id, source)
    store.session.commit()
    return source
