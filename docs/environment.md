# Environment configuration

Copy [the example](../.env.example) to `.env` when overriding development settings. Keep the file out of source control.

| Variable | Purpose |
|---|---|
| `APP_ORIGIN` | Exact public origin used by browser origin and mail-link checks |
| `FRONTEND_PORT` | Host port bound by Compose |
| `AGENTCITY_DOCKER_SUBNET` | Isolated Compose subnet |
| `DATABASE_URL`, `DB_PASSWORD` | Native database connection and Compose database password |
| `DEMO_ENABLED`, `ENABLE_REGISTRATION` | Controls public demo and sign-up |
| `COOKIE_SECURE`, `REQUIRE_EMAIL_VERIFICATION` | HTTPS cookie and signup verification policy |
| `SMTP_*` | Password reset and verification delivery |
| `PROVIDER_ENCRYPTION_KEY` | Fernet key for UI-managed provider credentials |
| `MODEL_ALLOWED_ORIGINS`, `MODEL_LOCAL_ORIGINS` | Additional server-approved model origins |
| `ALLOW_CLOUD_MODELS` | Server-level gate for workspace cloud consent |
| `DEMO_LOCAL_PROVIDER` | ID of the server-configured local provider available to demo sessions |
| `<PROVIDER>_MODEL`, `<PROVIDER>_BASE_URL`, `<PROVIDER>_API_KEY` | Optional server-managed providers |
| `EXTERNAL_WORKER`, `WORKER_CONCURRENCY`, `RUN_RETENTION_DAYS` | Queue execution mode, worker concurrency, and optional archive retention |
| `TELEMETRY_ORIGINS`, `NOTIFICATION_ORIGINS` | Approved origin lists for city data and external delivery |
| `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` | Optional single sign-on registration |
| `OTEL_ENABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `LOG_LEVEL` | Observability export and logging |
| `PUBLIC_PLANS` | Optional JSON list of access plans with `name`, `description`, and `price` |

`BACKEND_URL` is a frontend build/development setting. Compose builds the frontend with the name of the internal backend service.

