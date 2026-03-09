# PostgreSQL DB Wiring & JWT Session Persistence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix apparent data-loss between API restarts by explicitly setting `DATABASE_URL`, using a stable `SECRET_KEY`, and extending JWT lifetime to 7 days for local development.

**Architecture:** The Docker postgres:15 container already persists data correctly via a named volume. The root cause of "data loss" is a 30-minute JWT expiry — after a restart, the old token is invalid and the user appears logged out. We wire `.env` explicitly, add a convenience dev-start script with LAN-IP detection for mobile testing, and document the Vercel/Neon production switchover path.

**Tech Stack:** FastAPI, python-dotenv, SQLAlchemy 2.x, Docker Compose (postgres:15), uvicorn, React Native / Expo

---

### Task 1: Add explicit DB and auth vars to `.env`

**Files:**
- Modify: `plate-planner-api/.env`

**Step 1: Open `.env` and append the three new variables**

Add to the bottom of `plate-planner-api/.env`:

```dotenv
# ─── Database ───
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/plateplanner

# ─── Auth ───
# Fixed secret keeps JWTs valid across API restarts in dev.
# Generate a new random one for production: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=dev-fixed-secret-change-in-prod-aabbccddeeff00112233445566778899

# 7 days = 10080 minutes — eliminates re-login friction during development
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

**Step 2: Verify Docker is running and the DB is reachable**

```bash
docker-compose -f plate-planner-api/docker-compose.yml ps
```

Expected: `plate-planner-db` shows `Up` (or `running`).

```bash
docker exec -it plate-planner-db psql -U postgres -c "\l"
```

Expected: `plateplanner` database listed.

**Step 3: Restart the API and confirm it loads the new vars**

```bash
cd plate-planner-api
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

Inspect startup logs — should NOT show any `DATABASE_URL` connection errors.

**Step 4: Commit**

```bash
git add plate-planner-api/.env
git commit -m "config: set explicit DATABASE_URL, fixed SECRET_KEY, 7-day JWT in .env"
```

---

### Task 2: Create a dev-start convenience script with LAN-IP detection

**Files:**
- Create: `plate-planner-api/start-dev.sh`

**Step 1: Write the script**

Create `plate-planner-api/start-dev.sh`:

```bash
#!/usr/bin/env bash
# start-dev.sh — Start the API and print the LAN IP for mobile device testing.
set -e

# Detect Mac LAN IP (en0) or fall back to hostname -I on Linux
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo ""
echo "====================================================="
echo "  PlatePlanner API starting..."
echo "  Local:   http://localhost:8000"
echo "  Mobile:  http://$LAN_IP:8000"
echo ""
echo "  Set in mobile .env:  EXPO_PUBLIC_API_URL=http://$LAN_IP:8000"
echo "====================================================="
echo ""

uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --reload
```

**Step 2: Make it executable**

```bash
chmod +x plate-planner-api/start-dev.sh
```

**Step 3: Run it and verify output**

```bash
./plate-planner-api/start-dev.sh
```

Expected: Prints banner with LAN IP, then uvicorn starts without errors.

**Step 4: Commit**

```bash
git add plate-planner-api/start-dev.sh
git commit -m "chore: add start-dev.sh with LAN-IP banner for mobile testing"
```

---

### Task 3: Verify end-to-end session persistence

**Files:** None (manual verification only)

**Step 1: Register a test user**

With the API running, call the register endpoint:

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"persist-test@example.com","password":"Test1234!","name":"Persist Test"}' \
  | python3 -m json.tool
```

Expected: `201` with a `user_id` field.

**Step 2: Login and save the token**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"persist-test@example.com","password":"Test1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo "Token: $TOKEN"
```

Expected: Non-empty JWT string.

**Step 3: Stop the API (Ctrl+C) and restart it**

```bash
./plate-planner-api/start-dev.sh
```

**Step 4: Login again with the same credentials**

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"persist-test@example.com","password":"Test1234!"}' \
  | python3 -m json.tool
```

Expected: `200` with a new JWT — proves the user row survived the restart.

**Step 5: Confirm the original JWT is still valid (7-day window)**

```bash
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/users/me \
  | python3 -m json.tool
```

Expected: `200` with user profile — proves the fixed `SECRET_KEY` makes tokens durable across restarts.

---

### Task 4: Add a `.env.example` file for onboarding

**Files:**
- Create: `plate-planner-api/.env.example`

**Step 1: Write the example file**

Create `plate-planner-api/.env.example`:

```dotenv
# Copy this file to .env and fill in your values.
# Never commit .env to git.

# ─── External Recipe APIs ───
SPOONACULAR_API_KEY=your_spoonacular_key_here

# ─── LLM / AI Configuration ───
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_MODEL=gemini-2.5-flash

# ─── Neo4j ───
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_neo4j_password

# ─── Database ───
# Local dev: use the Docker postgres container
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/plateplanner
# Production (Vercel/Neon): replace with your Neon connection string
# DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-1.aws.neon.tech/neondb?sslmode=require

# ─── Auth ───
# Dev: use any stable string (keeps JWTs valid across restarts)
# Prod: generate with:  python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=dev-fixed-secret-change-in-prod-aabbccddeeff00112233445566778899
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

**Step 2: Verify `.env` is in `.gitignore`**

```bash
grep -n ".env" plate-planner-api/.gitignore
```

Expected: `.env` (and NOT `.env.example`) appears — so secrets stay local.

If `.gitignore` doesn't exist or is missing `.env`:

```bash
echo ".env" >> plate-planner-api/.gitignore
```

**Step 3: Commit**

```bash
git add plate-planner-api/.env.example plate-planner-api/.gitignore
git commit -m "docs: add .env.example with Neon/Vercel production path documented"
```

---

### Task 5: Document the Vercel/Neon production switchover

**Files:**
- Create: `docs/README-database.md`

**Step 1: Write the doc**

Create `docs/README-database.md`:

```markdown
# Database — Local Dev and Production

## Local Development

The API connects to a Docker-managed postgres:15 container.

```bash
# Start all services (DB, Neo4j, API)
docker-compose -f plate-planner-api/docker-compose.yml up -d

# Start the API with LAN-IP banner (for mobile device testing)
./plate-planner-api/start-dev.sh
```

Data is stored in the `postgres_data` Docker volume and **persists across container restarts**.

## Production — Vercel + Neon (Postgres)

1. Go to your Vercel project → **Storage** → **Connect Database** → **Postgres (Neon)**
2. Copy the `DATABASE_URL` Vercel generates
3. Add it to Vercel **Environment Variables** (Settings → Environment Variables)
4. Add a production `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
5. Set `ACCESS_TOKEN_EXPIRE_MINUTES=1440` (24 hours) for production

No code changes needed — `src/config/config.py` reads `DATABASE_URL` from the environment.

## Schema Migrations

`src/database/schema_guards.py` runs additive-only migrations at startup
(`ALTER TABLE ADD COLUMN IF NOT EXISTS`). No DROP TABLE logic exists.

When adding new columns, add them to `schema_guards.py` — they apply automatically on the next deploy.
```

**Step 2: Commit**

```bash
git add docs/README-database.md
git commit -m "docs: add README-database.md covering Docker dev and Vercel/Neon production"
```

---

## Verification Checklist

Before closing this plan:

- [ ] `plate-planner-api/.env` contains `DATABASE_URL`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- [ ] API starts without DB connection errors
- [ ] Register → Login → Restart API → Login again returns 200 (user row persisted)
- [ ] Old JWT still valid after API restart (fixed `SECRET_KEY` working)
- [ ] `start-dev.sh` prints correct LAN IP and starts uvicorn
- [ ] `.env.example` committed; `.env` is gitignored
- [ ] `docs/README-database.md` documents Neon switchover

---

## Production Secret Key Reminder

Before any real deployment:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Replace the dev placeholder in Vercel environment variables. **Never ship the dev key to production.**
