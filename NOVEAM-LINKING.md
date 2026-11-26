# NOVEAM API manager linking

Implemented 2026-11-17. Local integration preparation; no production traffic was switched.

## Connection model

The dashboard at `http://127.0.0.1:3000` sends same-origin admin requests through Vite to the manager at `http://127.0.0.1:8002`. The manager uses `NOVIOKRO_SERVICE_NOVEAM_BACKEND` to locate NOVEAM. The new **NOVEAM API linking** panel checks catalog availability, imports the catalog, and displays saved backend routes.

The manager first requests `/api.json` for compatibility with the existing custom frontend catalog. Only an HTTP 404 triggers a request to `/openapi.json`, which the native FastAPI backend exposes. OpenAPI discovery imports `/api/` operations, methods and query parameter names. It does not execute registration, login, or other discovered operations. Catalog availability is not a database-health check.

The professional categories integration now uses the same configured NOVEAM backend rather than a hardcoded production destination. Manager admin keys are not forwarded upstream. Existing NOVEAM browser API settings, login, Bearer tokens, and application routes are unchanged. Gateway traffic switching remains disabled; this work does not establish an authenticated application proxy.

## Native Windows startup

Prerequisites: a reachable isolated NOVEAM backend on port 8000; Python dependencies from `Noviokro-RC1-Custom/backend/requirements.txt`; Node dashboard dependencies. Use a separate local manager database and a development-only admin key. Do not point test processes at production databases.

In a backend terminal, from `Noviokro-RC1-Custom/backend`, set process-local configuration and start the manager:

```powershell
$env:NOVIOKRO_SERVICE_NOVEAM_BACKEND='http://127.0.0.1:8000'
# Set NOVIOKRO_ADMIN_KEY securely to your existing local-development admin key.
# The manager rejects admin requests when that value is empty.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

In a second terminal, from `Noviokro-RC1-Custom/dashboard`:

```powershell
npm install
$env:NOVIOKRO_MANAGER_URL='http://127.0.0.1:8002'
npm run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:3000`, find **NOVEAM API linking**, enter the manager admin key, select **Check NOVEAM connection**, then **Import NOVEAM API catalog**. A successful import displays the discovered route count and paths. The key stays in React memory, not browser storage. Vite now defaults to a loopback manager target for native development; the Compose dashboard explicitly retains `http://manager:8002`.

For Docker, use the nested `.env.example` as the template and set a local admin key. Its NOVEAM address uses `host.docker.internal:8000` to reach a backend running on Windows. Existing Compose database/loopback port settings are retained.

## Verification and current blockers

Seven isolated Python tests passed against the actual linking functions and metadata converter: query extraction, input validation and catalog bounds, 404-only OpenAPI fallback, custom catalog compatibility, no fallback after authorization failure, configured category destination/admin rejection, and unavailable catalog status. An additional FastAPI/MockTransport fallback regression was added to the framework suite but could not run here.

Python syntax and Vite configuration syntax were checked. Full FastAPI/SQLAlchemy tests and the React/Vite build remain unverified because those dependencies are absent. Docker is also unavailable on the command path. Browser control returned an unavailable host, so the manager UI could not be opened or visually verified. The manager is not running, and no live discovery was performed. This is prepared linking code, not a verified live connection.

Run the available contract checks from the workspace root:

```powershell
python noviokro-noveam-integration/Noviokro-RC1-Custom/backend/tests/check_noveam_link_isolated.py
```

After dependencies are installed, run `pytest -q tests/test_integrations_v04.py` from the manager backend and `npm run build` from the dashboard, then test the local connection using the panel. A successful full integration run is still required before changing NOVEAM's traffic destination.

## HTTP API calling and routing (2026-11-17)

The dedicated opt-in route is now implemented:

`NOVEAM local frontend → http://127.0.0.1:8002/noveam/api/... → configured NOVEAM backend /api/...`

The manager's existing admin-only proxies are unchanged. The new route forwards the user's Authorization header to NOVEAM and relies on NOVEAM to authorize each operation. It strips manager admin keys, cookies, forwarding headers, hop-by-hop headers and upstream redirects/cookies. Query strings, methods, JSON/multipart bodies, response types and error statuses are retained. Requests are bounded to 25 MiB and responses to 64 MiB; long responses time out after 30 seconds of transport inactivity. It does not cache responses.

It is disabled until `NOVIOKRO_NOVEAM_GATEWAY_ENABLED=1` is set in the manager's process environment. Set `NOVIOKRO_SERVICE_NOVEAM_BACKEND` to the selected NOVEAM origin before restarting the manager. HTTP is accepted only for loopback upstreams; remote backends require HTTPS. For a backend on another container, use HTTPS or provide a trusted loopback forwarding endpoint; the dedicated gateway intentionally rejects `http://host.docker.internal:8000` (catalog-only discovery remains compatible with that Docker URL).

Example for native development, from the manager backend directory:

```powershell
$env:NOVIOKRO_SERVICE_NOVEAM_BACKEND='http://127.0.0.1:8000' # or the explicitly selected HTTPS staging/deployed origin
$env:NOVIOKRO_NOVEAM_GATEWAY_ENABLED='1'
# Retain your manager's existing admin key/database configuration.
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

Restart the existing manager rather than starting a second process on port 8002. An existing `.env` file must be loaded by the launcher; plain uvicorn does not automatically load it. Do not replace an existing secret or database setting when enabling the gateway.

Serve this workspace's NOVEAM frontend on port 5500. Open `http://127.0.0.1:5500/login.html?gateway=noviokro` to opt that tab into gateway mode. The selection is retained in sessionStorage across page navigation. `?gateway=direct` clears it. Production frontend hosts ignore this local switch. No manager admin key is stored in NOVEAM or added to user requests.

The dashboard panel now includes an authenticated routing-configuration check. A manager without the new code returns 404 for `/api/v1/integrations/noveam/routing` and `/noveam/api/health`; restart/load this checkout before using gateway mode.

Scope: primary HTTP APIs only. Insights/Firebase requests retain their current destinations. WebSocket connections still use the direct NOVEAM backend; WebSocket tunneling has not been implemented. Thus, this is not a claim that every service or realtime transport has moved behind Noviokro.

Seven isolated tests exercise the actual gateway handler with a fake HTTP transport; four frontend routing regressions exercise the shared resolver. These pass without FastAPI installed locally. Live upstream calling is still unverified: at the latest check the manager's health endpoint returned 200, its new route returned 404, and port 8000 refused connections. The selected upstream and a manager restart are required for live verification. No production mutation was made.

```powershell
python noviokro-noveam-integration/Noviokro-RC1-Custom/backend/tests/check_noveam_gateway_isolated.py
node --test NOVEAM-frontend/noviokro-routing.test.cjs
```

## Selected local test connection

The user selected the local backend on 2026-11-17. The manager's ignored `.env` now contains:

- `NOVIOKRO_SERVICE_NOVEAM_BACKEND=http://127.0.0.1:8000`
- `NOVIOKRO_NOVEAM_GATEWAY_ENABLED=1`
- the two loopback frontend origins on port 5500.

No admin key or database credential was added to that file. `Start-LocalGateway.ps1` applies these local settings directly to the launched process (plain uvicorn does not read `.env` automatically). It uses a separate manager SQLite file under `.local-state`, preserves the admin key supplied in the terminal, and binds only to loopback. Stop the previous manager process before launching it; the script does not terminate an unidentified existing process.

From the workspace root, after installing manager requirements and supplying the existing local admin key in the terminal:

```powershell
.\noviokro-noveam-integration\Start-LocalGateway.ps1 -PythonExe '.\.qa-venv\Scripts\python.exe'
```

Start the actual NOVEAM backend separately against an isolated local PostgreSQL database. The manager's SQLite state is not a substitute for NOVEAM's PostgreSQL database. Then call `http://127.0.0.1:8002/noveam/api/health`, and open `http://127.0.0.1:5500/login.html?gateway=noviokro`.

Current live verification remains blocked: port 8000 refused connections, the old manager returned 404 for the new gateway route, and the available Python environment could not install FastAPI from the package index. Local configuration is saved, but no successful live gateway-to-backend request has been observed.
