# Noviokro v1.8.0 — Security readiness test foundation

Additive release based on v1.7.0. All earlier routes, bots, GUI and NUI retained. No live NOVEAM or Noveomediater connections enabled.

## New endpoint
`GET /api/v1/v18/security-readiness` with `x-admin-key` header. Read-only security configuration inventory. It deliberately reports `production_ready: false` and never returns secret values.

## Added tests
Authentication, secret redaction, conservative readiness reporting, invalid upstream URL schemes, and embedded credential rejection.

## Verify
`cd backend && python -m pytest -q`
`cd dashboard && npm ci && npm run build` (requires a generated npm lockfile; otherwise use `npm install` first)
`docker compose config --quiet && docker compose up --build` on a Docker-equipped machine.

## Still required
Real PostgreSQL service test, Docker startup, React build, browser E2E, realistic load tests, independent security review, user-scoped RBAC and production-grade distributed limiting. This is NOT production ready.
