# Testing

Install backend dev requirements and run `python -m pytest`. The test suite uses a temporary SQLite database and mocks provider HTTP responses. It exercises simulation determinism, fallback, endpoint validation, authentication, tenant isolation, ingest, scenario execution, SSE, approval, and export.

Autonomous-run tests reject a fictitious simulated route, exercise corrective execution, confirm a bounded stop when a baseline remains invalid, and verify fallback to pinned inputs, partial completion, and cancellation of an active lease.

Local protocol fixtures cover REST, WebSocket, MQTT, webhook delivery, and binary GTFS-Realtime. The identity fixtures exercise email verification and a PKCE exchange with a signed ID token. Backend tests verify calibration, the print-ready report, experiment archives, static GTFS imports, and API credential permissions. The frontend suite checks literal translation keys in both catalogs. Browser tests exercise the demo, mobile navigation, organization administration, telemetry, sensor coverage, the Model Lab, research variants, transit imports, and credential revocation.

Run `npm --prefix frontend test` for component and locale tests. Use `npx playwright install chromium` from `frontend` to install the browser if needed. Start the demo and run `npm --prefix frontend run e2e` for the command center, mobile navigation, localization, and organization flow. Set `AGENTCITY_TEST_URL` to check an alternate port. For PostGIS validation, start Compose and run the same browser tests against its frontend.

