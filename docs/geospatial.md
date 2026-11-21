# Geospatial data

Use WGS84 coordinates in longitude, latitude order. New city projects may include a road graph and positive demand pairs. A graph edge is `[from, to, free_flow_minutes, capacity, shape]`, where shape contains optional intermediate coordinates. To run a simulation, routes must connect each input demand pair.

Source imports support GeoJSON FeatureCollections of points, lines, and polygons, CSV with name, longitude and latitude columns, arrays of JSON named points, and GTFS `shapes.txt`. Import boundary polygons into **City boundary**. The map also has an optional **Sensor coverage** layer based on each online sensor’s reported radius. Imported geometry is stored in PostGIS when PostgreSQL is connected. Removing a source removes its features from the active map. [Example GeoJSON](../examples/demo-sensor.geojson)

In **Settings → Data sources**, choose **GTFS Schedule ZIP** to add scheduled routes and stops to the **Transit** layer and **Mobility** view. The archive needs `routes.txt`, `trips.txt`, `stops.txt`, and `stop_times.txt` at its root. Include `shapes.txt` for published alignments. When shapes are absent, the map labels the line connecting ordered stops as approximate. The import supports up to 1.4 MB compressed, 12 MB across the parsed tables, and 4,000 map features. Scheduled records describe the published network and can appear alongside separately configured GTFS-Realtime positions and delays. [GTFS reference](https://gtfs.org/documentation/schedule/reference/) · [Simulated Debrecen transit archive](../examples/debrecen-transit.zip)

