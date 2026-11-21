import json
import random
from datetime import datetime
from itertools import pairwise

from .config import ROOT
from .db import Store, now

DEBRECEN = json.loads((ROOT / "data" / "debrecen.json").read_text(encoding="utf-8"))
LAYERS = (
    "Traffic",
    "Transit",
    "Incidents",
    "Air quality",
    "Environmental zones",
    "Sensors",
    "Campus activity",
    "Energy",
    "Construction",
    "Recommendations",
    "Predicted congestion",
    "Intervention paths",
    "Risk zones",
    "City boundary",
    "Sensor coverage",
)
SENSOR_OVERLAYS = {"Air quality": "Air quality", "Energy": "Energy", "Campus occupancy": "Campus activity"}


def cities(store: Store, scope: str):
    return [DEBRECEN, *store.list(scope, "city")]


def city_for(store: Store, scope: str, city_id: str):
    return DEBRECEN if city_id == "debrecen" else store.get(scope, "city", city_id)


def point(value, layer: str):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": value["coordinates"]},
        "properties": {
            "layer": layer,
            **{key: val for key, val in value.items() if key not in {"coordinates", "history"}},
        },
    }


def line(coordinates, layer: str, **properties):
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {"layer": layer, **properties},
    }


def city_layers(city, store: Store, scope: str):
    nodes = city["nodes"]
    features = [
        line([nodes[a], *shape, nodes[b]], "Traffic", id=f"{a}-{b}", pressure=(i * 13 + 34) % 90)
        for i, (a, b, _, _, shape) in enumerate(city["edges"])
    ]
    edges = {(a, b): [nodes[a], *shape, nodes[b]] for a, b, _, _, shape in city["edges"]}
    for transit in city["transit"]:
        route = []
        for a, b in pairwise(transit["nodes"]):
            segment = edges.get((a, b)) or list(reversed(edges.get((b, a), [nodes[b], nodes[a]])))
            route.extend(segment if not route else segment[1:])
        features.append(line(route, "Transit", name=transit["name"], color=transit["color"]))
        features.extend(point({"coordinates": nodes[stop], "name": stop}, "Transit") for stop in transit["nodes"])
    for item in city["incidents"]:
        features.append(point(item, "Incidents"))
        if item["type"] == "Construction":
            features.append(point(item, "Construction"))
    for item in city["sensors"]:
        features.append(point(item, "Sensors"))
        if item["type"] in SENSOR_OVERLAYS:
            features.append(point(item, SENSOR_OVERLAYS[item["type"]]))
    for district, lng, lat in city["districts"]:
        features.append(point({"coordinates": [lng, lat], "name": district}, "Districts"))
    if city["id"] == "debrecen":
        for layer, coords, name in [
            ("Environmental zones", [21.641, 47.559], "Nagyerdő green zone"),
            ("Campus activity", city["origin"], "University of Debrecen"),
        ]:
            features.append(point({"coordinates": coords, "name": name}, layer))
        for layer, name, ring in [
            (
                "Environmental zones",
                "Nagyerdő park",
                [
                    [21.623, 47.552],
                    [21.626, 47.562],
                    [21.640, 47.565],
                    [21.647, 47.556],
                    [21.639, 47.551],
                    [21.623, 47.552],
                ],
            ),
            (
                "Campus activity",
                "Demonstration campus zone",
                [
                    [21.616, 47.550],
                    [21.620, 47.556],
                    [21.630, 47.556],
                    [21.631, 47.549],
                    [21.623, 47.548],
                    [21.616, 47.550],
                ],
            ),
        ]:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                    "properties": {"layer": layer, "name": name},
                }
            )
    for source in store.list(scope, "source", city_id=city["id"]):
        features.extend(source["features"])
    from .telemetry import city_readings, transit_positions

    readings = city_readings(store, scope, city["id"])
    live = {row["sensor_id"] for row in readings}
    if live:
        features = [row for row in features if row["properties"].get("id") not in live]
        for entry in sensors(city, readings):
            if entry["id"] in live and entry["coordinates"]:
                features.append(point(entry, "Sensors"))
                if entry["type"] in SENSOR_OVERLAYS:
                    features.append(point(entry, SENSOR_OVERLAYS[entry["type"]]))
    for vehicle in transit_positions(store, scope, city["id"]):
        if vehicle["coordinates"]:
            features.append(point({**vehicle, "name": vehicle["route"] or vehicle["trip"]}, "Transit"))
    return {"type": "FeatureCollection", "features": features}


def sensors(city, live=()):
    result = []
    for item in city["sensors"]:
        rng = random.Random(item["id"])
        reading = item["reading"]
        history = (
            [
                {"hour": f"{hour:02d}:00", "value": round(reading * rng.uniform(0.78, 1.15), 1)}
                for hour in range(8, 18)
            ]
            if reading is not None
            else []
        )
        result.append({**item, "history": history, "source": "Simulated"})
    listed = {entry["id"]: entry for entry in result}
    for row in live:
        key = row["sensor_id"]
        previous = listed.get(key, {})
        age = (now() - datetime.fromisoformat(row["observed_at"])).total_seconds()
        online = row["value"] is not None and -300 <= age <= 900
        listed[key] = {
            "id": key,
            "name": row["name"] or previous.get("name") or key,
            "type": row["type"] if row["type"] != "Sensor" else previous.get("type", "Sensor"),
            "coordinates": row["coordinates"] or previous.get("coordinates"),
            "unit": row["unit"] or previous.get("unit", ""),
            "reading": row["value"],
            "uptime": row.get("uptime"),
            "radius": row["radius"],
            "confidence": row.get("confidence"),
            "online": online,
            "history": [
                {"hour": entry["observed_at"][11:16], "observed_at": entry["observed_at"], "value": entry["value"]}
                for entry in row["history"]
                if entry["value"] is not None
            ],
            "source": row["source"],
            "observed_at": row["observed_at"],
        }
    return list(listed.values())
