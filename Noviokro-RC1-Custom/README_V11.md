# Noviokro v1.1.0 — Local Gateway Foundation (additive)

This copy was built from the supplied v1.0.0 standalone archive. Existing endpoints, bot modules, dashboard and integration configuration are retained. NOVEAM and Noveomediater production services were not contacted or modified.

## Included
- Adds `npm run build` and `npm run preview` to the React dashboard scripts (build requires Node dependencies).
- Corrects generated OpenAPI operation IDs for the existing multi-method gateway proxy without changing its methods or forwarding logic.
- Adds `GET /api/v1/v11/gateway/configuration` (admin-key protected): lists operator-configured upstream names, not secrets.
- Adds `POST /api/v1/v11/gateway/staging-health` (admin-key protected): opt-in, GET `/health` only against named operator-configured upstreams; 3-second timeout, no redirects or forwarded credentials. Disabled by default.
- Adds automated regression/security tests.

## Run
Copy `.env.example` to `.env`, set strong local secrets, then `docker compose up --build`. Dashboard: http://127.0.0.1:3000; API docs: http://127.0.0.1:8002/docs.

Run backend tests from project root:
`PYTHONPATH=backend python -m pytest backend/tests -q` (PowerShell: `$env:PYTHONPATH='backend'; python -m pytest backend/tests -q`).

To run a staging health check, configure `UPSTREAM_DEMO=https://your-authorized-staging.example` and `NOVIOKRO_ENABLE_STAGING_CHECKS=1` in `.env`; POST `{"upstream":"demo"}` with `X-Admin-Key` header. HTTP upstreams additionally require `NOVIOKRO_ALLOW_HTTP_STAGING=1` for explicitly approved local testing. **Do not configure public or untrusted upstreams.**

## Known limitations / security warning
This is not a production-ready gateway. Legacy gateway routes remain protected by a shared admin key, route definitions are in memory, and the original proxy does not yet have production-grade SSRF/DNS rebinding defenses, per-user RBAC, streaming, retries, distributed rate limiting, load testing, or high availability. The new health-check endpoint also relies on operator-configured URLs and does not pin DNS or block private-network destinations. Do not expose it publicly. Docker startup, browser testing and live staging requests have not been verified here.
