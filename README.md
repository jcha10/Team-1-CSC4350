# Smiley

An employee engagement platform, built over five sprints. This is the
state of the project at the end of **Sprint 1**.

- **Accounts and login.** Sign in and out, sessions that expire and can
  be revoked, and a lockout after repeated failed logins.

## Local development

```bash
# Backend (terminal 1)
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env            # turns on demo accounts for local use
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

The Vite dev server proxies `/api` and `/ws` to the backend, so dev runs
same-origin. No CORS setup is needed.

## Demo accounts

With `SEED_DEMO_DATA=true` (set by `.env.example`), these accounts are
created on an empty database. The password for all of them is
`password123`.

| username | role |
|---|---|
| alice, bob, carol, dave | employee |
| hr_admin | hr_admin |

## Configuration

All settings are environment variables (or `backend/.env` for local dev),
defined in [`backend/app/config.py`](backend/app/config.py):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./smiley.db` | SQLAlchemy URL |
| `SEED_DEMO_DATA` | `false` | Create the demo accounts on an empty DB. **Never in production.** |
| `SESSION_TTL_HOURS` | `12` | Login session lifetime |
| `LOGIN_MAX_FAILURES` / `LOGIN_LOCKOUT_MINUTES` | `5` / `15` | Brute-force lockout per (IP, username) |
| `CORS_ORIGINS` | empty | Only needed if the frontend runs on a different origin |
| `FRONTEND_DIST` | `frontend/dist` | Built app to serve (skipped if missing) |

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q     # 10 tests
cd frontend && npm run build
```
