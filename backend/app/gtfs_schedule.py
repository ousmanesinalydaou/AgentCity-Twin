"""Import map features and route summaries from a GTFS Schedule ZIP."""

import base64
import binascii
import csv
import io
import re
from collections import defaultdict
from zipfile import BadZipFile, ZipFile

MAX_ARCHIVE = 1_400_000
MAX_EXPANDED = 12_000_000
MAX_FEATURES = 4_000
MODES = {
    "0": "Tram",
    "1": "Metro",
    "2": "Train",
    "3": "Bus",
    "4": "Ferry",
    "5": "Cable tram",
    "6": "Aerial lift",
    "7": "Funicular",
    "11": "Trolleybus",
    "12": "Monorail",
}
FILES = ("routes.txt", "trips.txt", "stops.txt", "stop_times.txt", "shapes.txt")


def table(archive, filename):
    with archive.open(filename) as raw, io.TextIOWrapper(raw, encoding="utf-8-sig", newline="") as content:
        yield from csv.DictReader(content)


def feature(kind, coordinates, **properties):
    return {"geometry": {"type": kind, "coordinates": coordinates}, "properties": properties}


def import_schedule(encoded):
    try:
        if len(encoded) > (MAX_ARCHIVE + 2) // 3 * 4:
            raise ValueError("The GTFS ZIP must be under 1.4 MB.")
        data = base64.b64decode(encoded, validate=True)
        if len(data) > MAX_ARCHIVE:
            raise ValueError("The GTFS ZIP must be under 1.4 MB.")
        with ZipFile(io.BytesIO(data)) as archive:
            entries = [entry for entry in archive.infolist() if entry.filename in FILES]
            names = {entry.filename for entry in entries}
            required = {"routes.txt", "trips.txt", "stops.txt", "stop_times.txt"}
            if not required <= names or len(names) != len(entries):
                raise ValueError(
                    "Include single GTFS routes, trips, stops, and stop times tables at the ZIP root."
                )
            if sum(entry.file_size for entry in entries) > MAX_EXPANDED:
                raise ValueError("The GTFS tables exceed the expanded size limit.")
            return parse_schedule(archive, names)
    except (
        BadZipFile,
        RuntimeError,
        KeyError,
        TypeError,
        AttributeError,
        csv.Error,
        UnicodeError,
        binascii.Error,
        NotImplementedError,
    ) as exc:
        raise ValueError("The GTFS ZIP or its tables are invalid.") from exc


def parse_schedule(archive, names):
    routes, stops, trips = {}, {}, {}
    features = []
    for row in table(archive, "routes.txt"):
        key = row["route_id"]
        color = row.get("route_color") or ""
        routes[key] = {
            "route_id": key,
            "name": (row.get("route_short_name") or row.get("route_long_name") or key)[:120],
            "mode": MODES.get(row["route_type"], "Transit"),
            "color": f"#{color}" if re.fullmatch(r"[0-9a-fA-F]{6}", color) else "#ae8bfa",
            "frequency": None,
            "stop_count": 0,
        }
    for row in table(archive, "stops.txt"):
        if row.get("location_type") not in (None, "", "0", "1"):
            continue
        if not row.get("stop_lon") or not row.get("stop_lat"):
            continue
        key = row["stop_id"]
        coordinates = [float(row["stop_lon"]), float(row["stop_lat"])]
        stops[key] = coordinates
        features.append(feature("Point", coordinates, name=row["stop_name"], stop_id=key))
    for row in table(archive, "trips.txt"):
        trips[row["trip_id"]] = (row["route_id"], row.get("shape_id") or "")
        if row["route_id"] not in routes:
            raise ValueError("A GTFS trip references an unknown route.")
    if not routes or not trips or not stops:
        raise ValueError("Include at least one route, trip, and geolocated stop.")

    shapes = defaultdict(list)
    if "shapes.txt" in names:
        for row in table(archive, "shapes.txt"):
            shapes[row["shape_id"]].append(
                (int(row["shape_pt_sequence"]), [float(row["shape_pt_lon"]), float(row["shape_pt_lat"])])
            )
    route_stops = defaultdict(set)
    trip_stops = defaultdict(list)
    for row in table(archive, "stop_times.txt"):
        trip, stop = row["trip_id"], row["stop_id"]
        if trip not in trips:
            raise ValueError("A GTFS stop time references an unknown trip.")
        if stop in stops:
            route_stops[trips[trip][0]].add(stop)
            if trips[trip][1] not in shapes:
                trip_stops[trip].append((int(row["stop_sequence"]), stop))
    if not route_stops:
        raise ValueError("No GTFS stop times link trips to geolocated stops.")

    seen = set()
    for trip, (route, shape) in trips.items():
        sequence = tuple(stop for _, stop in sorted(trip_stops.get(trip, [])))
        key = (route, shape) if shape in shapes else (route, sequence)
        if key in seen:
            continue
        seen.add(key)
        if shape in shapes:
            coords = [point for _, point in sorted(shapes[shape], key=lambda entry: entry[0])]
        else:
            coords = [stops[stop] for stop in sequence]
        if len(coords) >= 2:
            features.append(
                feature(
                    "LineString",
                    coords,
                    name=routes[route]["name"],
                    route_id=route,
                    color=routes[route]["color"],
                    approximate=shape not in shapes,
                )
            )
    if len(features) > MAX_FEATURES:
        raise ValueError("The GTFS ZIP exceeds the limit of 4,000 map features.")
    for key, row in routes.items():
        row["stop_count"] = len(route_stops[key])
    return features, list(routes.values())
