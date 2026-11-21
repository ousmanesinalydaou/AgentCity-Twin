# Live operations

## City feeds

Sign in as an organization administrator and open **Settings → Live data feeds**. In Debrecen, **Start simulated feed** publishes clearly labeled sensor updates from the worker and provides a test of the event stream without external services.

For a live feed, add its exact origin to `TELEMETRY_ORIGINS`, then create a source for the city. REST and WebSocket payloads accept [the reading format](../examples/telemetry.json). MQTT reads the same JSON from one exact topic. Supply credentials through the feed form when required. GTFS-Realtime accepts a binary FeedMessage with vehicle positions and trip updates. Positions appear in Mobility and the Transit layer. Sensor histories expose timestamps and provenance, and the coverage planner ranks road-network gaps. Use a fresh timezone-aware timestamp in real feeds.

The worker polls approved sources on their configured interval. Synthetic readings remain labeled and do not overwrite observed readings. Fresh matching traffic-loop readings can adjust modeled demand relative to the demonstration baseline. [GTFS-Realtime bindings](https://gtfs.org/documentation/realtime/language-bindings/python/)

## Calibration

Open **Settings → Simulation calibration** and select a chronological JSON array of paired modeled and observed values. Each metric needs at least ten pairs. The uploaded source name, fitted coefficients, and held-out error are captured with subsequent runs. The comparison table and versioned report display empirical validation ranges where calibration exists. [Sample observations](../examples/calibration.json)

## Identity and invitations

Set `OIDC_ISSUER`, `OIDC_CLIENT_ID`, and `OIDC_CLIENT_SECRET` to activate single sign-on. Register the callback at `APP_ORIGIN/api/v1/auth/oidc/callback`. Use **Preferences → Link single sign-on** after signing in with a password to associate an existing account. For new users, **Settings → Invitations** creates revocable, single-use organization links. Configure SMTP to send invitations or enforce mailbox verification. The sign-in page can request a fresh verification link.

## Delivery channels

Configure delivery under **Settings → Notification delivery**. Email uses the configured SMTP service. Slack and Teams receive their webhook formats. The webhook, SMS, and push adapters send a JSON event to an approved integration bridge. Add its exact origin to `NOTIFICATION_ORIGINS`. The recipient system must provide the phone-number or device subscription routing. Delivery history shows queued, sent, cancelled, or failed events. An operator can also mark in-app alerts as read.

Subscribe to **Agent completed** or **Agent model failed** for individual specialist outcomes. A failed model advisory keeps the specialist’s rule-based finding available to the run. An agent with no eligible model can complete directly using rules. The in-app notification contains the specialist name and outcome. External channels receive the event type and city metadata.

## Shared workers and telemetry

Compose runs the API and the worker separately against PostgreSQL. The queue uses bounded leases with retries and records interrupted work. Backend instances share database-backed quotas. Set `RUN_RETENTION_DAYS` to remove terminal run archives after an explicit retention period. Expired identity tokens and telemetry events are swept automatically.

To collect local application metrics, set `OTEL_ENABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel:4318`, then run `docker compose --profile observability up --build --wait`. The collector exposes Prometheus metrics at `http://localhost:9464/metrics` and prints trace summaries to its logs. For shared infrastructure, configure an authorized OTLP receiver. [OpenTelemetry Python exporters](https://opentelemetry.io/docs/languages/python/exporters/)

