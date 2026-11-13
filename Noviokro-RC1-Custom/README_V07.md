# Noviokro v0.7.0 — Standalone additive extension

This release **copies** v0.6.0 to a new folder and adds `backend/app/v07.py` and a React panel. It does not change NOVEAM, Noveomediater, or earlier release folders.

## New capabilities
- Digital Marketing, Digital Branding, Public Relations, Press Coverage, Feedback and Suggestions bots: **deterministic brief drafting**, persisted in database. No model inference, media pitching, scraping, publication or invented coverage.
- Project-scoped role assignment records for standalone, NOVEAM and Noveomediater. **These records are administrative metadata, not yet enforced as per-user RBAC**. Existing v0.6 scoped bearer token enforcement remains.
- Offline QA workflow and stored monitoring summary; expanded React dashboard panel.
- Staging checks: disabled by default. The endpoint rejects unsafe hosts, but returns 501 rather than contacting the network until DNS-pinned transport is built. This prevents misleading security claims.
- Previous DevBot/TestBot offline workflows preserved.

## Run
Copy `.env.example` to `.env`; set `NOVIOKRO_ADMIN_KEY` (>=16 chars), `NOVIOKRO_V06_TOKEN_SECRET` (>=32 chars), and other existing v0.6 variables. Run `docker compose up --build`. Open `http://127.0.0.1:3000` or `http://127.0.0.1:8002/docs`. Create a v0.6 local token with `POST /api/v1/v06/local-token` and `X-Admin-Key` for the v0.7 panel. Use admin token for role creation, tester/admin for briefs and QA, and viewer+ for lists.

## Security and status
Local-only prototype. Do not publish ports publicly. Existing legacy key-protected endpoints are not migrated to per-user authentication. Do not use for live production routing or customer data. Separate configurations per project do not imply connected applications.
