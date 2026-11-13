# Noviokro v1.9.0 — isolated infrastructure verification

Additive release based on v1.8.0; no previous routes, bots or GUI/NUI removed. NOVEAM and Noveomediater integrations remain disconnected.

## Added
- Admin-only `GET /api/v1/v19/integration-readiness` conservative readiness inventory.
- Route catalog persistence regression test using isolated SQLite.
- PostgreSQL persistence integration test, activated only when `NOVIOKRO_TEST_POSTGRES_URL` is set.
- CI PostgreSQL service job; React npm build and Compose config jobs retained.

## Local verification
`cd backend && python -m pytest -q`
`cd dashboard && npm install --no-audit --no-fund && npm run build`
`docker compose config --quiet`

## Remaining work
Browser E2E, live Docker startup, realistic load testing, threat modeling and independent security review. The shared admin key and staging-only proxy are NOT production-ready.
