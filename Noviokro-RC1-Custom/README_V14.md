# Noviokro v1.4.0 — Staging Traffic Telemetry Foundation

This additive release retains the v1.3.0 source, routes, bots, GUI and NUI. NOVEAM and Noveomediater are not connected.

## Operator-only opt-in

Set `NOVIOKRO_ADMIN_KEY` to a strong secret. Set `NOVIOKRO_V14_DATABASE_URL` to a dedicated PostgreSQL database URL for shared-worker persistence (or SQLite for local testing). To record staging proxy request status and latency, set `NOVIOKRO_V14_ENABLE_TELEMETRY=1`. To enable shared database-backed per-route fixed-window limiting, also set `NOVIOKRO_V14_ENABLE_DB_RATE_LIMIT=1` and `NOVIOKRO_V14_RPM=30` (1–10000).

The middleware covers only `/api/v1/v12/proxy/{route}/{path}`. It stores the route name, response status, latency and timestamp; never request bodies, credentials, URLs, query strings or upstream hosts. GET `/api/v1/v14/traffic/standalone` requires `x-admin-key`. Other project names are rejected. Existing v1.2 in-memory rate limiting remains in place; this DB limiter is an additional guard. The limiter is fixed-window and records may grow without retention; not production hardened.

## Run backend regression tests

`cd backend && python -m pytest -q`

## Limitations

No automatic monitoring of the older `/gateway/` endpoint, no distributed tracing, no complete RBAC, no load testing, no browser validation, no verified live upstream traffic, no production approval. The database is initialized on request and has no schema migration or retention policy. A database outage can fail staging requests. Docker/React build verification depends on local tooling. Keep both live platform integrations disabled.
