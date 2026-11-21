# Deployment

Build the frontend, API, and worker images and apply Alembic migrations as a dedicated job. Serve the frontend through an HTTPS ingress. Keep the API, worker, and PostGIS on an internal network. Set `APP_ORIGIN` to the exact external origin and enable secure cookies. Enable SMTP for email-based flows and configure OIDC for single sign-on.

PostgreSQL coordinates worker leases and API quotas across replicas. Scale the worker service according to provider capacity and tune `WORKER_CONCURRENCY`. Configure approved outbound feed origins, notification destinations, archival retention, PostgreSQL backups, and an OTLP receiver. [Operational configuration](operations.md)

