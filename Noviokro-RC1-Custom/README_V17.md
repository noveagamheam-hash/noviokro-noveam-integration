# Noviokro v1.7.0 — Integration verification foundation

Additive update on v1.6.0; prior gateway, bots, GUI and NUI retained. No NOVEAM or Noveomediater connections are enabled.

## Added
- `GET /api/v1/v17/readiness` authenticated diagnostic (does not connect to the database or probe live services).
- Isolated tests for authentication, feature flags, and secret non-disclosure.
- GitHub Actions verification for backend regression, dashboard build and Docker Compose configuration.
- Docker Compose now explicitly sets the v1.2 route catalog database URL to the local PostgreSQL container.

## Verify on a connected development machine
- `cd backend && pip install -r requirements.txt && python -m pytest -q`
- `cd dashboard && npm install && npm run build`
- `docker compose config --quiet && docker compose up --build`
- Verify PostgreSQL persistence, browser flows, and upstream forwarding only in authorized isolated staging.

## Limitations
GitHub Actions scripts are included but have not been executed here. Local React build, Docker startup, PostgreSQL service integration, browser E2E, and load testing remain unverified. v1.7 is NOT production ready.
