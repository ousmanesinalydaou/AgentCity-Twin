# Implementation and runtime configuration

| Area | Implementation | Operational input |
|---|---|---|
| City data | Seeded and simulated telemetry, REST, WebSocket, MQTT, GTFS-Realtime, and demand-weighted sensor siting | Approve live endpoints and supply locally authorized credentials |
| Simulation | Deterministic network estimates, paired-measurement calibration, held-out residual ranges, and reproducibility metadata | Provide dated observations and validate the calibration against the local network |
| Model system | Structured advisories, benchmarks, vision, embeddings, read-only city tools, and text streaming | Configure models that support the required capabilities |
| Agent negotiation | Specialist dissent, proposed revision, second simulation, and scored comparison | Set objectives and constraints for each scenario |
| Autonomous execution | Persisted task plans, parallel specialist delegation, tool observations, bounded correction, cancellation, and verified completion criteria | Choose a scenario and inspect its execution plan |
| Model routing | Privacy, capability, context, language, cost, reasoning tier, and measured fallback | Supply provider metadata and choose routing limits |
| Map timeline | Modeled traffic, transit delay, emissions, incident phase, and intervention layers | Select the prediction or recommendation and a timeline point |
| Agent notifications | Distinct specialist completion and failure events with delivery subscriptions | Enable notifications and configure any external delivery channels |
| Identity | Password sessions, scoped invitations, and optional OIDC single sign-on | Supply an identity-provider registration and optional SMTP configuration |
| Operations | PostgreSQL worker leases, shared quotas, administrative audits, delivery outbox, retention, and OTLP export | Set retention windows and approved delivery destinations |
| Locales | English source text, French and Bambara catalogs, persisted selection | Review terminology with fluent local users before field use |
| Reports | Web comparison, JSON, CSV, and versioned print-ready operator and research documents | Choose a template and timeline point |
| Experiments | Named studies, saved scenario variants, comparative results, archive and restore, structured export | Supply experiment notes and choose reproducible inputs |
| Transit schedule | GTFS ZIP routes and stops, supplied shapes or labeled approximate routes | Upload the city’s published schedule |
| Integration access | Tenant-scoped, expiring read credentials with revocation | Choose the permissions and securely distribute each credential |
| Public site | Public demo, contact, registration, documentation, and optional access plans | Supply approved plan names, descriptions, and prices if plans are offered |

The default Debrecen scenario uses simulated inputs. Live integrations depend on the chosen service and credentials. The [operations guide](operations.md) describes the connection points and the simulated alternatives.

