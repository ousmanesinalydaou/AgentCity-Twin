"""Render a WebGL-free map preview from the same OpenStreetMap snapshot."""

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
folder = root / "frontend" / "public" / "maps"
data = json.loads((folder / "debrecen.geojson").read_text(encoding="utf-8"))
width, height = 1500, 960
image = Image.new("RGB", (width, height), "#0b1523")
draw = ImageDraw.Draw(image)
center = (21.6264, 47.5414)
scale = 19500


def project(coordinate):
    lng, lat = coordinate
    return (
        width / 2 + (lng - center[0]) * scale,
        height / 2 - (lat - center[1]) * scale / math.cos(math.radians(center[1])),
    )


def polygons(feature, color):
    geometry = feature["geometry"]
    points = geometry["coordinates"]
    for polygon in points if geometry["type"] == "MultiPolygon" else [points]:
        if len(polygon[0]) >= 3:
            draw.polygon([project(point) for point in polygon[0]], fill=color)


def lines(feature, color, thickness):
    geometry = feature["geometry"]
    points = geometry["coordinates"]
    for line in points if geometry["type"] == "MultiLineString" else [points]:
        draw.line([project(point) for point in line], fill=color, width=thickness, joint="curve")


fills = {"landuse": "#111d2c", "landcover": "#102923", "park": "#132f29", "water": "#112e45"}
road_colors = {
    "service": ("#1b2a3c", 1),
    "minor": ("#29384a", 2),
    "tertiary": ("#384b60", 3),
    "secondary": ("#42566b", 4),
    "primary": ("#526479", 5),
    "trunk": ("#526479", 5),
    "motorway": ("#526479", 5),
    "rail": ("#283848", 2),
}
for layer, color in fills.items():
    for item in data["features"]:
        if item["properties"]["layer"] == layer and "Polygon" in item["geometry"]["type"]:
            if layer == "landcover" and item["properties"]["class"] not in {"wood", "grass"}:
                continue
            polygons(item, color)
for category, (color, size) in road_colors.items():
    for item in data["features"]:
        if (
            item["properties"] == {"layer": "transportation", "class": category}
            and "LineString" in item["geometry"]["type"]
        ):
            lines(item, color, size)
image.save(folder / "debrecen.webp", quality=91)
