# PostgreSQL Database Wiring & Session Persistence Design

**Date:** 2026-03-08
**Status:** Approved
**Scope:** Local development — fix JWT expiry and explicit DB wiring

---

## Problem

Users experience apparent data loss after API restarts. Root cause: JWT access tokens expire after **30 minutes** (the default), so any app session or test that outlasts a restart appears to lose authentication — even though the PostgreSQL data itself is intact.

The Docker `plate-planner-db` container (postgres:15) already runs with a named volume (`postgres_data`) and persists data correctly. Twelve user rows confirmed present after investigation.

---

## Root Cause

| Symptom | Actual Cause |
|---------|-------------|
| "Data lost after restart" | JWT expires after 30 min; re-login required |
| "App can't connect to DB" | `DATABASE_URL` not set in local `.env`; code falls back to hardcoded default which works, but isn't explicit |
| "Each restart feels fresh" | Short token lifetime — login token is invalid before next session |

---

## Design

### Section 1 — Fix JWT Expiry and Explicit .env Wiring

Add the following to `plate-planner-api/.env`:

```
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/plateplanner

# Auth — use a fixed secret in dev so tokens survive restarts
SECRET_KEY=dev-fixed-secret-change-in-prod-32chars-min

# Extend tokens to 7 days for local dev
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

**Why a fixed `SECRET_KEY`:** If `SECRET_KEY` is randomly generated at startup (or missing), previously issued JWTs become invalid after every restart. A stable dev key makes tokens durable.

**Why 10080 minutes (7 days):** Eliminates the friction of re-logging-in during development while keeping a natural expiry for security hygiene.

---

### Section 2 — Mobile Real-Device Access

When testing the React Native app on a physical device, `localhost` in the API URL won't resolve. The API must:

1. Bind to `0.0.0.0` (already the default for `uvicorn` — no code change needed)
2. Be reachable via the Mac's LAN IP (e.g., `192.168.1.x`)

**Convenience script** — add to `plate-planner-api/start-dev.sh`:

```bash
#!/usr/bin/env bash
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}')
echo "API available at: http://$LAN_IP:8000"
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Set `EXPO_PUBLIC_API_URL=http://<LAN_IP>:8000` in the mobile `.env` when testing on device.

---

### Section 3 — Verification Flow

After applying the fix, verify end-to-end persistence:

1. Start Docker: `docker-compose up -d`
2. Start API with `.env` loaded
3. Register a new user → confirm 201
4. Login → receive JWT
5. Create a meal plan or pantry entry
6. Stop and restart the API (`Ctrl+C`, then restart)
7. Login again with same credentials → confirm 200 and same data returned

This proves both the DB and JWT wiring are correct.

---

### Section 4 — Production Path (Vercel + Neon)

When deploying to Vercel:

1. Create a **Vercel Postgres (Neon)** database in the Vercel dashboard
2. Copy the `DATABASE_URL` Vercel provides (postgres://... format)
3. Add it as a Vercel environment variable — no code changes needed
4. Set a production `SECRET_KEY` (random, ≥32 chars)
5. Set `ACCESS_TOKEN_EXPIRE_MINUTES=1440` (24h) for production

The SQLAlchemy session code reads `DATABASE_URL` from the environment, so switching from local Docker to Neon is purely a config change.

---

## Out of Scope

- Schema migrations (Alembic) — `schema_guards.py` handles additive changes safely
- Multi-region DB, connection pooling — premature for current scale
- Refresh token flow — 7-day expiry is sufficient for dev; production can revisit

---

## Files Changed

| File | Change |
|------|--------|
| `plate-planner-api/.env` | Add `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` |
| `plate-planner-api/start-dev.sh` | New convenience script printing LAN IP |
| `docs/README-database.md` (optional) | Document production Neon path |
