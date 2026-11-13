# Noviokro v1.5.0 — isolated staging diagnostics

Additive release based on v1.4.0. Existing routes, bots, GUI/NUI and staging controls are preserved. No NOVEAM/Noveomediater deployment or integration is performed.

## Added
- Authenticated `GET /api/v1/v15/status` returns safe configuration flags without credentials.
- Authenticated `GET /api/v1/v15/traffic-summary` aggregates existing v1.4 staging telemetry per route.
- Read-only React v1.5 staging dashboard; no write actions or live integrations.
- Three regression tests for access control, disabled telemetry, and persisted summary.

## Local verification
```sh
cd backend
python -m pytest -q
cd ../dashboard
npm ci # requires a package-lock.json; otherwise npm install
npm run build
```

## Docker
Copy `.env.example` to `.env`, configure secrets and use `docker compose up --build`. Docker must be installed and accessible. This has not been verified in this environment.

## Known limitations
- No real upstream forwarding, Docker runtime, browser, or PostgreSQL server integration test has been completed as part of this release.
- No production security audit, distributed load test or end-to-end RBAC verification.
- v1.4 telemetry is opt-in and covers only v1.2 staging proxy traffic; not global request tracing.
- Rate limiting depends on existing v1.4 behavior; this release does not redesign it.
- Admin key remains an interim local-development authentication mechanism.
- No claim of production readiness.
