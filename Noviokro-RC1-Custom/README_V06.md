# Noviokro v0.6.0 — standalone additive prototype

This release is copied into a **new folder** from v0.5.0. No NOVEAM, Noveomediater, or earlier Noviokro files are edited.

## New isolated v0.6 features
- Locally bootstrapped, signed, one-hour bearer tokens with viewer/tester/admin scopes, isolated to `/api/v1/v06/*`. This is **not** full enterprise OIDC/RBAC.
- QA Bot evaluates offline status/latency fixtures in a bounded subprocess (Linux CPU/memory limits where supported).
- Monitoring evaluates **submitted health snapshots only**. It does not poll live services, contact production endpoints, or collect real telemetry.
- New PostgreSQL `noviokro_v06_records` table stores QA results and monitoring evaluations.
- Previous v0.5 gateway, DevBot/TestBot, bot registry, React GUI, and integration routes are retained unchanged.

## Run locally (Windows + Docker)
1. Extract this archive to a NEW folder.
2. Copy `.env.example` to `.env`, replace `NOVIOKRO_ADMIN_KEY` and `NOVIOKRO_V06_TOKEN_SECRET` with independent strong random values.
3. Run `docker compose up --build`.
4. Open `http://127.0.0.1:8002/docs` and `http://127.0.0.1:3000`.
5. Use `POST /api/v1/v06/local-token` with header `X-Admin-Key` and JSON `{ "requested_role": "tester" }`; use returned bearer token in the v0.6 endpoints.
6. `POST /api/v1/v06/qa-runs` example: `{ "cases": [{ "name": "login", "expected_status": 200, "actual_status": 200, "max_latency_ms": 500, "actual_latency_ms": 120 }] }`.
7. `POST /api/v1/v06/monitoring/snapshots` example: `{ "service": "staging-api", "status_code": 200, "latency_ms": 120, "error_rate": 0.01 }`.

## Security limitations
- Not safe for public deployment: older routes still use development-only authentication; bootstrap admin key is a shared secret; token revocation, tenant isolation, OIDC and true role assignment are not implemented.
- Worker uses a separate process and resource limits, but **is not a secure arbitrary-code sandbox**. Arbitrary code execution is deliberately unsupported. For future execution of untrusted code use hardened container/VM isolation with no network, read-only filesystem, low-privilege user and cgroup limits.
- Monitoring is offline; live checks require explicit allowlisted test destinations and SSRF-resistant egress controls.
- `create_all` is development-only; production needs reviewed migrations.
