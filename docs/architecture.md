# Architecture

The Next.js application presents the map and workspace, while FastAPI owns scenario validation, permissions, persistence, and the decision workflow. Next.js proxies same-origin API requests and event streams to the internal backend service. MapLibre receives GeoJSON prepared by the backend and renders it against a basemap.

```mermaid
sequenceDiagram
  participant UI as City workspace
  participant A as FastAPI
  participant D as PostgreSQL
  participant W as Run worker
  UI->>A: Create scenario or analyze a prompt
  A->>D: Persist scenario, run, and input snapshot
  A-->>UI: 202 with run ID
  A->>W: Dispatch run
  UI->>A: Subscribe to run events
  W->>D: Persist execution events and final ranking
  A-->>UI: Stream recent and new persisted events
  UI->>A: Load result, explanation, or export
```

Docker runs an API and a separate PostgreSQL-backed worker service. A worker lease fences competing replicas, and expired leases can retry within a bounded attempt limit. The API streams persisted audit events independently of the worker. SQLite development runs an embedded worker.

