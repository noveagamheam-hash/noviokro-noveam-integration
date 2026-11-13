# Noviokro v1.0.0 — GUI/NUI local development milestone

This is an additive standalone development release copied from the v0.9.0 GUI/NUI package. Existing routes, bot logic, legacy panels and optional integrations remain unchanged. No NOVEAM or Noveomediater production services are connected.

## Included
- New React management console: v0.8 username/password login, project selector, read-only project monitoring, QA reports, press evidence, legacy bot history, gateway route registry and discovery catalog.
- Existing typed NUI navigation, optional browser speech input, accessibility preferences and older React panels preserved.
- New `GET /api/v1/v10/monitoring/{project}` requiring v0.8 project-scoped bearer authentication. Legacy QA counts are exposed only to standalone members.
- Legacy route/bot/discovery read-only views still require `NOVIOKRO_ADMIN_KEY` (separate from v0.8 identity).

## Run locally
1. Copy `.env.example` to `.env`, configure strong `NOVIOKRO_ADMIN_KEY` and `NOVIOKRO_V08_TOKEN_SECRET`.
2. Run `docker compose up --build`.
3. Open `http://127.0.0.1:3000` and `http://127.0.0.1:8002/docs`.
4. Bootstrap an initial administrator via the documented v0.8 endpoint with the configured admin key, then sign in from the new management panel.

## Limitations
- This is **not** a production-ready v1 gateway or a completed autonomous NUI system.
- The new panel is read-only; existing older panels retain their previous controls and security boundaries.
- Staging checks remain disabled; the new summary does not probe remote services.
- Existing v0.8 login is local development authentication, not a fully hardened identity platform.
- Existing discovery implementation is retained; a new from-scratch active discovery engine is **not** claimed in this GUI/NUI milestone.
- Do not publish Docker ports to the internet without an independent security review.
