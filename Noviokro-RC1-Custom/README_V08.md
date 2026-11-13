# Noviokro v0.8.0 — Standalone additive extension

This folder is an independent copy of v0.7.0, not an overwrite. All previous API routes and modules remain included. NOVEAM and Noveomediater are **project labels**, not live integrations.

## Additions
- Independent v0.8 identity: bootstrap first administrator (requires existing `X-Admin-Key`), login with salted PBKDF2 passwords, 30-minute signed bearer tokens, project memberships and enforced permissions on **new v0.8 endpoints**.
- QA dashboard: reads previous offline QA results for the standalone project. Earlier QA records have no project identity and are intentionally not shown for NOVEAM/Noveomediater.
- Press evidence: accepts user-provided HTTPS source URLs, records them as unverified, and supports a manual reviewer status. It does not research, crawl, validate, or claim media coverage.
- Optional Ollama AI draft endpoint: disabled by default; only talks to `127.0.0.1:11434` inside the backend container, so Ollama must be reachable there (e.g. via a sidecar or container network namespace). Model outputs require human review.
- React v0.8 panel: role display, QA results, and press evidence submission.

## Run
1. Extract to a NEW directory.
2. `Copy-Item .env.example .env` then replace ALL placeholder secrets with unique random values.
3. `docker compose up --build`.
4. Open `http://127.0.0.1:8002/docs` to bootstrap via `/api/v1/v08/identity/bootstrap` using the admin key, then login at `/api/v1/v08/identity/login`.
5. Use the bearer token in the new React v0.8 panel at `http://127.0.0.1:3000`.

## Security and limits
- All previous v0.1–v0.7 routes are preserved **with their existing development-level authentication**. The new RBAC does not secure legacy endpoints.
- Do not expose this stack to the public internet or run it against production services.
- Local Ollama is opt-in and may require container networking configuration; it is not automatically available.
- Existing staging checks remain disabled. A DNS-pinned transport and staging-only allowlists must be implemented before enabling live checks.
- No automated publishing, journalist outreach, autonomous repository edits, arbitrary code execution or verified press-coverage research is implemented.
- The application currently uses `create_all` for new tables rather than a reviewed migration system. Back up data before upgrades.
- Automated tests cover only a subset of the behavior; production hardening, threat modeling and load testing remain outstanding.
