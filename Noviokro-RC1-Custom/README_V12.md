# Noviokro v1.2.0 — additive staging gateway foundation

This package extends v1.1.0. No existing gateway or bot routes were deleted. It is **not production-ready**. NOVEAM and Noveomediater are not connected.

## Added
- `GET /api/v1/v12/routes`: admin-key-protected persistent route catalog.
- `POST /api/v1/v12/routes`: create a disabled-by-default staging route with an operator-configured upstream.
- `DELETE /api/v1/v12/routes/{name}`: delete a v1.2 route.
- `/api/v1/v12/proxy/{name}/{path}`: opt-in guarded staging forwarding for enabled routes; disabled by default.
- Simple in-process per-route 60-second request limiter; NOT distributed or production-grade.
- Database via SQLAlchemy: set `NOVIOKRO_V12_DATABASE_URL` to PostgreSQL connection string (`postgresql+psycopg://...`) for persistence, or use the default local SQLite file. This database is separate from existing app databases.

## Configuration
Use a strong `NOVIOKRO_ADMIN_KEY`. Never expose it to untrusted clients. Configure `UPSTREAM_DEMO=https://<operator-approved-ip>`; no user-supplied destination URLs. `NOVIOKRO_V12_ENABLE_PROXY=1` is required to permit forwarding. Routes are created disabled and this release has no enable endpoint: enabling requires explicit manual DB administration after review, by design. `NOVIOKRO_ALLOW_HTTP_STAGING=1` allows HTTP and `NOVIOKRO_ALLOW_LOOPBACK_STAGING=1` permits loopback IPs for local tests. Leave both off otherwise.

The proxy refuses hostname upstreams (IP literals only) to avoid DNS rebinding. This means HTTPS certificate hostname validation may fail for many upstreams. Do not disable TLS verification to work around it. Add a reviewed pinned-DNS transport before real staging use. Rate limiting is local memory only, not cross-instance. No per-user RBAC is enforced on these endpoints: they use the existing administrator key. Do not use this service as a public internet gateway.

## Tests
Run from `backend`: `PYTHONPATH=. pytest -q`. On this build: 33 passed. Docker and browser integration and actual upstream forwarding were not tested.
