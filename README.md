# Smiley

An employee engagement platform with two faces:

- **Smile Mode** (every employee): a live, gamified leaderboard across six
  metrics, levels, achievement badges, daily streaks, peer kudos, a private
  to-do list, and company announcements. Employees can hide any metric from
  the *public peer leaderboard*, one metric at a time.
- **Predatory Mode** (`hr_admin` only): a monitoring dashboard over a
  simulated activity stream, where restricted keywords ("job search",
  "steam", "resume", …) flag employees for HR. It shows KPI tiles, a
  per-employee violation chart, a violations-over-time chart, a searchable
  live feed, and drill-down employee rows. Violations can also post real
  Slack alerts.

**Transparency by design.** The visibility toggles never pretend to be a
monitoring opt-out. The UI says plainly that they control only what peers
see, and that company monitoring continues regardless. The code enforces
the same split: the monitoring pipeline never reads visibility settings.
See [Security model](#security-model).

---

## Quickstart (Docker)

```bash
docker compose up --build
```

Open **http://localhost:8000**. The compose file enables demo mode by
default, so these accounts exist (password `password123`):

| username | role |
|---|---|
| alice, bob, carol, dave | employee |
| hr_admin | hr_admin |

In the app header, triple-click the 😊 logo as `hr_admin` to switch into
Predatory Mode. The server decides who is allowed; the click just asks.

The whole product is one container on one port: FastAPI serves the API,
the WebSockets, and the built React app. Data lives in the `smiley-data`
volume at `/data/smiley.db`.

## Deploying for real

```bash
# 1. Start without the well-known demo accounts
SEED_DEMO_DATA=false docker compose up -d --build

# 2. Create real accounts (password is prompted, never echoed)
docker compose exec smiley python -m app.cli create-user dana --role hr_admin
docker compose exec smiley python -m app.cli create-user sam  --role employee

# Other account operations
docker compose exec smiley python -m app.cli list-users
docker compose exec smiley python -m app.cli reset-password sam   # also signs sam out everywhere
```

Put it behind a TLS-terminating reverse proxy (nginx, Caddy, a cloud load
balancer). The container runs uvicorn with `--proxy-headers`, so login
throttling sees the real client IP. The WebSocket paths live under `/ws/`
and need your proxy's usual WebSocket upgrade settings.

**Backups:** the entire state is one SQLite file in the `smiley-data`
volume. Copy `/data/smiley.db` from the volume, or run `sqlite3 .backup`
against it.

**Building behind a TLS-inspecting corporate proxy:** pass your CA bundle as
a build secret. It is used for `npm ci` / `pip install` only and is never
stored in an image layer:

```bash
docker build --secret id=extra_ca,src=/path/to/ca-bundle.crt -t smiley .
```

## Configuration

All settings are environment variables (or `backend/.env` for local dev),
defined in [`backend/app/config.py`](backend/app/config.py):

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./smiley.db` (container: `/data/smiley.db`) | SQLAlchemy URL |
| `SEED_DEMO_DATA` | `false` (compose: `true`) | Create the demo accounts on an empty DB. **Never in production.** |
| `SESSION_TTL_HOURS` | `12` | Login session lifetime |
| `LOGIN_MAX_FAILURES` / `LOGIN_LOCKOUT_MINUTES` | `5` / `15` | Brute-force lockout per (IP, username) |
| `SLACK_WEBHOOK_URL` | unset | Post violation alerts to Slack (see below) |
| `SIMULATOR_ENABLED` / `SIMULATOR_INTERVAL_SECONDS` | `true` / `4` | Simulated activity stream |
| `CORS_ORIGINS` | empty | Only needed if the frontend runs on a different origin |
| `FRONTEND_DIST` | `frontend/dist` | Built app to serve (skipped if missing) |

### Slack alerts

Create an [Incoming Webhook](https://api.slack.com/messaging/webhooks) in
a Slack workspace **you control**, then set `SLACK_WEBHOOK_URL`. Every new
violation now makes a real POST to Slack, and the Predatory Mode badge
turns green. With the variable unset, alerts go to the server log instead
and nothing else changes. A failing webhook is logged and never stalls the
simulator.

## Local development

```bash
# Backend (terminal 1)
cd backend
python3.11 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env            # turns on demo accounts for local use
.venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

The Vite dev server proxies `/api` and `/ws` to the backend, so dev runs
same-origin, exactly like production. No CORS setup is needed.

## Tests & CI

```bash
cd backend && .venv/bin/python -m pytest -q     # 37 tests
cd frontend && npm run build
```

The suite covers login, logout, session expiry, lockout, and hashed-only
token storage. It checks that every HR route and WebSocket returns 403
(or a 1008 close) to employees, that visibility filtering hides a user from
peers but not from HR, that task privacy holds (another user's task
returns 404, even for `hr_admin`), and that kudos limits, streak math, the
keyword scanner, and the account CLI all behave. It also includes a
regression test for a simulator crash that used to kill the background
task after its first tick.

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs the backend
tests, the frontend build, and a Docker build plus health-check smoke test
on every push.

## Security model

- **Authentication.** A random 256-bit bearer token is issued at login.
  Only its SHA-256 hash is stored (`auth_sessions` table), with an expiry,
  so sessions survive restarts, logout revokes them server-side, and a
  database copy can't be replayed. Passwords use bcrypt. A failed login
  takes the same time whether or not the username exists, and repeated
  failures lock out that (IP, username) pair.
- **Authorization.** A single dependency, `require_hr_admin`
  ([`auth.py`](backend/app/auth.py)), guards every `/api/hr/*` route,
  `POST /api/announcements`, and `/ws/hr/feed`. It checks the role
  **stored in the database**, never anything the client sends. The
  frontend's hidden toggle calls `GET /api/hr/verify` before switching
  views, and every Predatory Mode request is re-checked independently.
- **Visibility vs. monitoring.** `metric_visibilities` is read in exactly
  one place: the peer leaderboard query. The telemetry simulator, the
  `activity_logs` table, and the `is_disloyal` flag never consult it. An
  employee who hides everything from peers is monitored exactly like one
  who hides nothing, and the UI states this at the toggle.
- **Private data.** Tasks are scoped to their owner on every route. No
  route, including any HR route, lists another user's tasks. Streaks and
  kudos are social features that HR routes never read.
- **Hardening.** Input length limits on every write, `nosniff` /
  `X-Frame-Options: DENY` / `no-referrer` headers, a non-root container
  user, and demo accounts off by default with a loud log warning when
  they're enabled.

## Architecture

```
 Browser (React SPA) ──REST /api/*──►  FastAPI (single process, one port)  ──SQLAlchemy──►  SQLite (/data)
        ▲                               ├─ REST routes + RBAC                                users, auth_sessions,
        └──────WebSocket /ws/*─────────┤─ WebSocket fan-out (leaderboard, HR feed)          metric_visibilities,
                                        ├─ background telemetry simulator ──► Slack webhook  activity_logs, kudos,
                                        └─ static files: built frontend                      tasks, announcements
```

WebSockets reconnect with exponential backoff after a server restart, and
stop retrying when the server closes with 1008 (not authorized). Any 401
during a session, from an expired, revoked, or reset session, sends the UI
back to the login screen instead of leaving a dashboard that silently
stops updating.

## Project layout

```
Dockerfile, docker-compose.yml, .github/workflows/ci.yml
backend/
  app/
    config.py         every environment setting, in one place
    main.py           routes, WebSockets, lifespan, static frontend
    auth.py           sessions, login throttling, require_hr_admin
    users.py / cli.py account creation + operator CLI
    models.py         SQLAlchemy tables      schemas.py  request/response models
    telemetry.py      simulator + keyword scanner
    notifications.py  Slack webhook + log fallback
    engagement.py     streaks + kudos limits   seed.py  demo accounts
  tests/              pytest suite
frontend/src/
  api.js              API client (same-origin), 401 -> logout event
  useLiveSocket.js    reconnecting WebSocket hook
  App.jsx             session + mode state     components/  UI
```

## Known limitations

- **Single process.** Login throttling and WebSocket fan-out live in one
  process's memory, so run one replica. Scaling out would need Redis (or
  similar) for both, plus Postgres instead of SQLite via `DATABASE_URL`.
- **No migrations yet.** Tables are created on startup, and new columns are
  not added to an existing database. That's fine for a first launch;
  add Alembic before the next schema change.
- **Simulated activity.** The monitored activity stream is generated, not
  captured from real browsers, by design.
- **Accounts come from the CLI.** There is no self-service signup and no
  in-app password change yet.
