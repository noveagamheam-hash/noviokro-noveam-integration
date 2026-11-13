# Noviokro v1.6.0 — isolated staging verification

Additive release based on v1.5.0. All prior API routes, bots and dashboard components remain present. No NOVEAM or Noveomediater connection is enabled.

## Added
- Authenticated `GET /api/v1/v16/preflight` with sanitized staging configuration flags and explicit remaining release gates.
- Automated gateway integration tests using an in-process HTTPX mock upstream: request method, body, query forwarding, sensitive admin header stripping, unauthorized requests, disabled-proxy fail-closed behavior.
- Existing backend regression suite remains runnable with `cd backend && PYTHONPATH=. pytest -q`.

## Verification caveats
- Mock upstream tests do **not** prove real network forwarding, DNS rebinding resistance or external connectivity.
- Real PostgreSQL, Docker Compose startup, browser end-to-end and load testing require separately available services and tooling.
- Do not enable the staging proxy on a public endpoint or connect production services without security review.
- React dashboard uses `cd dashboard && npm install && npm run build` for a production build; test results depend on dependency availability.
