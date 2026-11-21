# API

Start the stack and open [the OpenAPI browser](http://localhost:3100/api-docs). Versioned endpoints are under `/api/v1`.

| Workflow | Endpoints |
|---|---|
| Session | `POST /auth/bootstrap`, `POST /auth/demo`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/resend-verification`, `GET /auth/me` |
| City | `GET /cities`, `GET /cities/{id}/layers`, `GET /incidents`, `GET /sensors`, `GET /mobility` |
| Scenario | `POST /scenarios`, `POST /scenarios/{id}/run`, `POST /agentcity/analyze` |
| Debrecen demo presets | `GET /scenarios/demo`, `POST /scenarios/demo/{id}/run` with `workspace_id` |
| Result | `GET /simulations/{id}`, `GET /simulations/{id}/results`, `GET /simulations/{id}/events` |
| Execution plan | `GET /simulations/{id}/execution`, `POST /simulations/{id}/cancel` |
| Report | `GET /reports/{id}`, `GET /reports/{id}?format=csv`, `POST /simulations/{id}/approval` |
| Printable reports | `GET /reports/{id}/document?template=research&minute=30&language=fr` |
| Live city data | `/telemetry/feeds`, `/telemetry/demo-feed`, `/telemetry/events`, `/telemetry/vehicles`, `/telemetry/coverage` |
| Model lab | `POST /model-lab/tasks`, `/model-lab/benchmarks` |
| Experiments | `GET /experiments`, `POST /experiments`, `GET /experiments/{id}`, `PUT /experiments/{id}`, `POST /experiments/{id}/variants?start=true`, `GET /experiments/{id}/export` |
| Calibration | `/calibration/{city_id}` |
| Identity | `/auth/oidc/status`, `/auth/oidc/start`, `/auth/oidc/callback`, `/invitations`, `POST /auth/invite` |
| Operations | `/operations/features`, `/operations/admin`, `/notification-settings/channels`, `POST /notification-settings/read` |
| Administration | `/users`, `/teams`, `/workspaces`, `/agents`, `/providers`, `/settings/policy`, `/data-sources` |
| API credentials | `GET /api-credentials`, `POST /api-credentials`, `DELETE /api-credentials/{id}` |

Run creation returns HTTP 202 and a run ID. The SSE stream accepts `Last-Event-ID` and ends with a `done` event. The workspace uses API polling if the stream disconnects. Model and report endpoints inherit session and tenant checks.

The run's `status` tracks the worker job. The `execution.state` field tracks plan progress and distinguishes partial completion or pending operator review after the job returns results. Events with `stage: "execution"` carry plan updates in `data.execution`. Read the full plan from the execution endpoint or JSON report.

Organization administrators can issue API credentials for 1 to 90 days in **Settings → API credentials**. Copy the token when issued and supply it in the `Authorization: Bearer <token>` header. The available scopes cover city and mobility reads, experiment and scenario reads, and simulation and report reads. Connections using these credentials can make 120 permitted requests per minute. Revocation takes effect on subsequent requests. Requests that mutate data continue to require an authorized browser session.

