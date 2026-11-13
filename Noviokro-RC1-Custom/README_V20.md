# Noviokro AI API Manager 2.0.0 RC1

This standalone release candidate is based on the v1.9.0 Infrastructure
Verification ZIP. It adds the admin-only `GET /api/v2/release-readiness`
endpoint. Pass the configured `NOVIOKRO_ADMIN_KEY` in the `X-Admin-Key` header.
The endpoint returns a static verification checklist and reports
`production_ready: false`. It performs no network or database checks.

## Local verification on Windows

From a fresh extraction, use PowerShell with Python, Node.js and Docker Desktop.

1. Install the backend dependencies with
   `py -m pip install -r backend/requirements.txt`. From `backend`, run
   `py -m pytest -q`. The PostgreSQL test skips unless
   `NOVIOKRO_TEST_POSTGRES_URL` points to an isolated test database. CI provides
   that database for the PostgreSQL job.
2. From `dashboard`, run `npm.cmd install` and `npm.cmd run build`.
3. From the project root, copy `.env.example` to `.env` and replace the
   placeholder credentials. Leave the NOVEAM and Noveomediater URLs commented
   out. Use the Compose-managed local PostgreSQL instance.
4. Run `docker compose config --quiet` and `docker compose up --build -d`.
   Compose installs dashboard dependencies in a Docker volume so the Linux
   container can run alongside a native Windows dashboard build.
   Check the gateway at `http://127.0.0.1:8002/health` and exercise the GUI
   and NUI at `http://127.0.0.1:3000`. Use `docker compose down` when done.

Record the results of PostgreSQL persistence, the full Compose startup, browser
flows, load testing and independent security review before a production release.

## NOVEAM custom API catalog

To opt in, set `NOVIOKRO_SERVICE_NOVEAM_BACKEND=https://noveam.in` in `.env`
and rebuild the manager with `docker compose up -d --build manager`.
The NOVEAM integration reads `/api.json` from that origin. The document must
have `format: "noviokro-api/1"`, `app: "noveam"`, and a `routes` array.
Routes include an ID, HTTP method, path, query parameter names and summary.

In `/docs`, supply your `X-Admin-Key` and run
`GET /api/v1/integrations/health/noveam/backend` to check the HTTP status of the
catalog. Then call `POST /api/v1/integrations/discover` with
`{"project":"noveam","service":"backend"}` to validate and store the catalog.
Discovery only reads the catalog. It does not execute the listed routes.
