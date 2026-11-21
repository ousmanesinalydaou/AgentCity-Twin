# Database

Docker uses PostgreSQL 16 with PostGIS. Alembic migrations create an indexed `records` table for tenant-scoped documents and a `city_geometries` table with a GiST index for imported map features. The primary record key is `(scope, kind, key)`. Indexed type and time support workspace listing. Sessions store hashed tokens and expiry timestamps. Run input snapshots and analysis outputs are persisted separately.

GeoJSON upload writes the source metadata and corresponding PostGIS features in one transaction. Local SQLite development stores the same workspace records and GeoJSON payloads without the PostGIS projection. Use a dedicated PostGIS database to test geospatial persistence and back up the volume before upgrades in a deployment.

