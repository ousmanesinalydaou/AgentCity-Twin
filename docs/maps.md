# Maps

The default Debrecen map uses a small reproducible OpenStreetMap snapshot sourced via OpenFreeMap. MapLibre supports panning, zoom, fly-to, bearing, pitch, fullscreen, clusters, and layer management. The map can display measured or imported geometry alongside scenario overlays, selected locations, sensor points, and modeled effects. The current, predicted, and recommended states use the same geographic reference.

In organization settings, choose the local map, Fiord, Dark or Liberty. Online styles use OpenFreeMap vector tiles. When the upstream tiles contain building heights, the online map renders extrusion above zoom 14. The georeferenced snapshot is limited to Debrecen. Map assets credit OpenStreetMap contributors and OpenFreeMap.

**Predicted** and **Recommended** show the selected simulation frame. The timeline updates modeled traffic, estimated delay on transit routes intersecting the scenario area, the modeled emissions change within that area, and the incident’s active or recovery phase. Click a feature for its frame value. The emissions overlay depicts the scenario estimate as an area indicator. Live sensor readings and GTFS-Realtime positions retain their observations and timestamps.

