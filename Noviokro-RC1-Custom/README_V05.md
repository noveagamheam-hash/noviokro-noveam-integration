# Noviokro v0.5.0 — standalone additive sandbox release

This is a NEW independent folder copied from the earlier local Noviokro prototype. It does not connect to, edit, or deploy NOVEAM, Noveomediater, or earlier Noviokro installations.

## New capabilities
- Persistent DevBot/TestBot configurations, sandbox execution results, and audit events in **new** `noviokro_v05_*` tables.
- DevBot **offline OpenAPI path linting** (missing operation IDs and response declarations).
- TestBot **offline fixture assertions** (expected versus actual HTTP status codes provided in JSON).
- Expanded React GUI for creating sandbox bots, submitting fixtures, viewing runs and basic monitoring.
- Separate viewer/admin keys on the new `/api/v1/sandbox/*` namespace; write operations require admin.
- No shell execution, arbitrary Python execution, filesystem mutations, outbound calls, or actual AI inference.

## Run locally
1. Extract into a new directory; do not overwrite any existing project.
2. Copy `.env.example` to `.env`. Set a random `NOVIOKRO_ADMIN_KEY` of at least 16 characters. Optionally set `NOVIOKRO_VIEWER_KEY` to a distinct strong key.
3. `docker compose up --build`
4. Open http://127.0.0.1:3000 and http://127.0.0.1:8002/docs
5. For TestBot fixture use `{ "cases": [{ "name": "login", "expected_status": 200, "actual_status": 200 }] }`.
6. For DevBot fixture use `{ "paths": { "/health": { "get": { "responses": { "200": {} } } } } }`.

## Boundaries and security
- This is an offline deterministic **sandbox prototype**, not autonomous coding or a real API load-testing agent.
- All old routes remain available as before; they use their previous development-only authentication. New scoped keys protect only the new sandbox namespace.
- The existing v0.2/v0.3/v0.4 components still have development security limitations. Do not expose the Docker stack publicly.
- `create_all` only creates missing new tables in this local development project; it is not a production migration system.
- For production: implement OIDC/RBAC, tenant scoping, secret storage, network egress policy, isolated workers, approval gates, and reviewed migrations.
