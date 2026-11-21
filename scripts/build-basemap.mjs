import { createRequire } from "node:module";
import { writeFile, mkdir } from "node:fs/promises";

const require = createRequire(new URL("../frontend/package.json", import.meta.url));
const { VectorTile } = require("@mapbox/vector-tile");
const { default: Pbf } = require("pbf");
const target = new URL("../frontend/public/maps/", import.meta.url);
await mkdir(target, { recursive: true });
const response = await fetch("https://tiles.openfreemap.org/planet");
if (!response.ok) throw Error("TileJSON unavailable");
const catalog = await response.json();
const zoom = 14;
function tile(lng, lat) {
  const rad = lat * Math.PI / 180;
  return [Math.floor((lng + 180) / 360 * 2 ** zoom),
    Math.floor((1 - Math.asinh(Math.tan(rad)) / Math.PI) / 2 * 2 ** zoom)];
}
const [minX, minY] = tile(21.563, 47.588);
const [maxX, maxY] = tile(21.687, 47.494);
function round(value) {
  return Array.isArray(value) ? value.map(round) : +value.toFixed(5);
}
async function load(x, y) {
  const response = await fetch(catalog.tiles[0].replace("{z}", zoom).replace("{x}", x).replace("{y}", y));
  if (!response.ok) throw Error("Vector tile unavailable");
  const tile = new VectorTile(new Pbf(new Uint8Array(await response.arrayBuffer())));
  const output = [];
  const names = ["transportation", "landcover", "landuse", "water", "waterway", "park"];
  for (const name of names) {
    const layer = tile.layers[name];
    if (!layer) continue;
    for (let index = 0; index < layer.length; index++) {
      const item = layer.feature(index);
      const category = item.properties.class || item.properties.subclass || "";
      if (name === "transportation" && ["path", "track", "pier", "aerialway", "ferry"].includes(category)) continue;
      if (name === "landuse" && !["residential", "industrial", "commercial", "cemetery", "hospital", "school"].includes(category)) continue;
      const feature = item.toGeoJSON(x, y, zoom);
      if (feature.geometry.type === "Point") continue;
      output.push({ type: "Feature", geometry: { ...feature.geometry, coordinates: round(feature.geometry.coordinates) },
        properties: { layer: name, class: category } });
    }
  }
  return output;
}
const jobs = [];
for (let x = minX; x <= maxX; x++) {
  for (let y = minY; y <= maxY; y++) jobs.push(load(x, y));
}
const features = (await Promise.all(jobs)).flat();
await writeFile(new URL("debrecen.geojson", target), JSON.stringify({ type: "FeatureCollection", features }));
console.log("Saved", features.length, "OpenStreetMap features from OpenFreeMap.");

