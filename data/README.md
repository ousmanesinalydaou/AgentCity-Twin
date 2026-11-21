# Data sources

`debrecen.json` is the seeded urban simulation model. Incidents, route capacities, demand, sensor readings, and district telemetry are synthetic and labeled as such in the app.

The Debrecen basemap in `frontend/public/maps` is an aggregated OpenStreetMap snapshot via OpenFreeMap. Data credits are rendered on the map. Use `node scripts/build-basemap.mjs` to refresh the GeoJSON and `python scripts/render-basemap.py` with Pillow to rebuild the fallback image. The bundled Noto Sans map glyphs were sourced from the OpenFreeMap glyph service. Noto Sans is distributed under the SIL Open Font License.


The OpenStreetMap-derived GeoJSON snapshot is distributed under the [Open Database License](https://opendatacommons.org/licenses/odbl/1-0/). [OpenStreetMap copyright and attribution](https://www.openstreetmap.org/copyright)
