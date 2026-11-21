# Docker Compose

Run `docker compose up --build --wait` and browse to http://localhost:3100. The database health check runs before the migration job. FastAPI starts after migration, and Next.js starts after the API is healthy. Inspect services with `docker compose ps` and logs with `docker compose logs backend`.

Port 3100 binds to loopback. To change it, set both `FRONTEND_PORT` and `APP_ORIGIN` in your environment or `.env`. The Compose network defaults to `10.196.213.0/24` and can be changed with `AGENTCITY_DOCKER_SUBNET` if that range is already occupied.

On Docker Desktop, the backend uses the host's LM Studio server at `http://host.docker.internal:1234/v1`. Start the server and load `prism-ml/bonsai-27b` before running a scenario. The demo uses this server-configured local provider for specialist advisories. Set `DEMO_LOCAL_PROVIDER=` to run demo advisories with deterministic rules alone. [LM Studio server guide](https://lmstudio.ai/docs/developer/core/server)

`docker compose down` stops the stack and preserves the named PostGIS volume.

