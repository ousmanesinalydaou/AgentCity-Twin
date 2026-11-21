# Backend

FastAPI owns typed request validation, tenant permissions, storage, outbound configuration, and versioned API routes. SQLAlchemy scopes records to organizations. Dedicated workers claim Postgres-backed run leases, publish streamed audit events, poll configured city feeds, and retry notification delivery. SQLite supports the same workflows through a local embedded worker.

`/api/v1/health` probes the database. **Settings → Operations** displays administrative event history and active workers. Optional OTLP traces and metrics cover requests, runs, and execution events. See [operations](operations.md).

