# Noviokro v1.3.0 — Monitoring and audit development increment

This is an **additive** release based on v1.2.0. It preserves existing routes, bots, GUI/NUI and gateway. No NOVEAM or Noveomediater production integration is enabled.

## New features
- `POST /api/v1/v13/observations`: operator-submitted staging observation (project, route, status code, latency).
- `GET /api/v1/v13/monitoring/{project}`: bounded recent sample, mean latency, count of 5xx statuses.
- `GET /api/v1/v13/audit/{project}`: audit events for observation submission.
- React monitoring panel with a project selector, submission form and recent history.
- Persistent SQLAlchemy storage using `NOVIOKRO_V13_DATABASE_URL`, falling back to `NOVIOKRO_V12_DATABASE_URL` or local SQLite.

All new endpoints require `X-Admin-Key` matching `NOVIOKRO_ADMIN_KEY`. Use a separate strong secret; the browser stores the key only in component memory. Do not expose this interface on a public network.

**Limits:** Monitoring is based on manually submitted results, not automatic gateway traffic capture. Audit events cover only v1.3 observation submissions. Rate limiting remains v1.2 process-local. Distributed limiting, automatic tracing, production security, DNS-pinned proxying, real load tests and full RBAC are not complete.

## Local test

```bash
cd backend
python -m pytest -q
```

For local deployment use the existing `docker compose up --build` workflow and environment setup in previous READMEs. React build requires npm dependencies and `npm run build` from `dashboard`.
