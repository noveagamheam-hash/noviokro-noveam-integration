# Noviokro AI API Manager v0.3.0 (additive)

This release is a **separate copy** of v0.2.0. The original endpoints and prototype are preserved. No production services are accessed or changed.

## New functionality
- PostgreSQL persistence for **new v0.3** model configurations, approvals, and audit entries (v0.2 in-memory routes/bots/feedback remain in-memory).
- Local Ollama adapter (disabled by default). It requires a separate reachable Ollama service on Docker DNS name `ollama`; no Ollama service is bundled or downloaded.
- Human approval state transitions. **Approving does not execute bot actions.**
- React/Vite read-only development dashboard for bots, approvals and models.
- Three additional tests.

## Windows 11 Docker setup
1. Install Docker Desktop; extract ZIP.
2. Copy `.env.example` to `.env` and replace the admin key with a random secret.
3. Run `docker compose up --build` in this directory.
4. Open http://127.0.0.1:3000 (dashboard) or http://127.0.0.1:8002/docs (API).
5. Enter the same admin key in the dashboard to load data.

**Security:** This is local-development software, not production-ready. Dashboard uses a shared admin key in memory; no OIDC, tenant RBAC, secure secrets vault, migration tool, distributed queues, or production gateway hardening yet. Docker database password is a local-only example. Keep all ports bound to localhost. Do not expose to the public internet.

## Tests
`cd backend && pip install -r requirements.txt && pytest -q`

## Compatibility and limitations
- Existing v0.2 APIs are not changed.
- New tables use `noviokro_v03_` prefix; `create_all` only creates absent tables. Production deployments should use reviewed versioned migrations instead.
- New v0.3 endpoints live under `/api/v1/next` to avoid collisions.
- This package is a starter, not a complete enterprise AI multi-bot gateway.


## v0.4.0: Additive NOVEAM + Noveomediater adapters
- No existing endpoints or app files were edited; the v0.3 project was copied into this release.
- New API namespace `/api/v1/integrations`: `GET /projects`, `POST /discover`, `GET /discoveries`, `GET /health/{project}/{service}`.
- Only explicit operator-configured **staging** upstreams are contacted. No arbitrary URLs or gateway traffic switching.
- The `POST /discover` operation reads `/openapi.json`, stores a bounded endpoint catalog in a new `noviokro_v04_discoveries` table, and never calls discovered application operations.
- Read-only React dashboard section displays discovered APIs. Existing Bot/Approval/Model sections retained.
- No production credentials, NOVEAM authentication flow changes, or Noveomediater modifications.
- For a local staging FastAPI instance listening on host port 9000, set `NOVIOKRO_SERVICE_NOVEAM_BACKEND=http://host.docker.internal:9000` in `.env` before running Docker. Likewise use `NOVIOKRO_SERVICE_NOVEOMEDIATER_BACKEND` for the other staging service.
- In `/docs`, authorize with `X-Admin-Key` and call `POST /api/v1/integrations/discover` with `{ "project": "noveam", "service": "backend" }`.
- `GET /api/v1/integrations/health/noveam/backend` checks the staging `/health` endpoint.
- OpenAPI catalogs may expose sensitive endpoint names; restrict admin access and keep this development stack bound to localhost.
- **Limitations:** Operator-configured URLs require network-level egress restrictions in real deployments; a single shared development admin key is not production-grade. Database schema is added using development-only `create_all`, not production migrations. Bot tools remain approval-only.
