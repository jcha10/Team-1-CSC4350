"""
FastAPI application entrypoint.

Route map:
  POST /api/auth/login                  -> exchange credentials for a bearer token (throttled)
  POST /api/auth/logout                 -> revoke the caller's session server-side
  GET  /api/health                      -> liveness + DB check; reports whether demo mode is on
  GET  /api/me                          -> current user's own profile + visibility settings
  PATCH /api/me/visibility              -> toggle public leaderboard visibility for ONE metric
  GET  /api/leaderboard/{metric}        -> ranked list, excluding users who hid that metric
  POST /api/kudos/{username}            -> send a peer a cheer (1 per pair per rolling 24h)
  GET  /api/tasks                       -> the caller's own private to-do list
  POST /api/tasks                       -> create a task for the caller
  PATCH /api/tasks/{task_id}            -> toggle is_done on a task the caller owns
  DELETE /api/tasks/{task_id}           -> delete a task the caller owns
  GET  /api/announcements               -> company-wide posts, readable by any authenticated user
  POST /api/announcements               -> [hr_admin only] publish a new announcement
  GET  /api/hr/verify                   -> 200 iff caller is hr_admin, used by the hidden mode-switch
  GET  /api/hr/telemetry                -> [hr_admin only] recent raw activity log (?flagged= to filter)
  GET  /api/hr/employees/{u}/activity   -> [hr_admin only] one person's full activity log
  GET  /api/hr/disloyalty-stats         -> [hr_admin only] per-person violation counts
  GET  /api/hr/employees                -> [hr_admin only] full employee telemetry table
  GET  /api/hr/integrations/status      -> [hr_admin only] whether the Slack alert webhook is configured
  WS   /ws/leaderboard?token=...        -> push notifications when leaderboard standings change
  WS   /ws/hr/feed?token=...            -> [hr_admin only] live raw activity stream
  GET  /*                               -> the built React app (when frontend/dist exists)

RBAC in one sentence: every /api/hr/* route, POST /api/announcements, and
the /ws/hr/feed socket depend on `require_hr_admin` (see auth.py), which
raises 403 unless the role stored in the database is "hr_admin".
"""
import asyncio
import contextlib
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import config, engagement, models, notifications, schemas, telemetry
from .auth import (
    authenticate,
    bearer_token,
    clear_login_failures,
    create_session,
    ensure_login_allowed,
    get_current_user,
    get_user_from_ws_token,
    record_login_failure,
    require_hr_admin,
    revoke_session,
)
from .database import Base, SessionLocal, engine, get_db
from .seed import seed_if_empty

# Without this, our own loggers (e.g. notifications.py's Slack fallback
# line) are silently dropped - the root logger defaults to WARNING with no
# handler, and uvicorn only configures its own "uvicorn.*" loggers.
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


# ---------------------------------------------------------------------------
# WebSocket connection manager (broadcast fan-out)
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict):
        # Iterate a copy: connect/disconnect can run while we await a send.
        for ws in list(self.connections):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


leaderboard_manager = ConnectionManager()
hr_manager = ConnectionManager()


# ---------------------------------------------------------------------------
# App lifecycle: schema, optional demo seed, background telemetry simulator
# ---------------------------------------------------------------------------
@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if config.SEED_DEMO_DATA:
        db = SessionLocal()
        try:
            seed_if_empty(db)
        finally:
            db.close()

    simulator = None
    if config.SIMULATOR_ENABLED:
        simulator = asyncio.create_task(
            telemetry.run_simulator(
                session_factory=SessionLocal,
                broadcast_hr=hr_manager.broadcast,
                broadcast_leaderboard=leaderboard_manager.broadcast,
                interval_seconds=config.SIMULATOR_INTERVAL_SECONDS,
            )
        )
    yield
    if simulator:
        simulator.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await simulator


app = FastAPI(title="Smiley", lifespan=lifespan)

if config.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    return response


def user_out(user: models.User) -> schemas.UserOut:
    """
    Serialize a user with a visibility entry for EVERY leaderboard metric.
    A metric with no stored row is public - rows only exist once someone
    has toggled that metric - so new accounts and newly added metrics
    default to visible without needing backfilled rows.
    """
    stored = {v.metric: v.is_public for v in user.visibilities}
    data = schemas.UserOut.model_validate(user).model_dump()
    data["visibilities"] = [{"metric": m, "is_public": stored.get(m, True)} for m in models.LEADERBOARD_METRICS]
    return schemas.UserOut(**data)


# ---------------------------------------------------------------------------
# Auth + profile
# ---------------------------------------------------------------------------
@app.post("/api/auth/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    throttle_key = (request.client.host if request.client else "unknown", payload.username.lower())
    ensure_login_allowed(throttle_key)

    user = authenticate(db, payload.username, payload.password)
    if user is None:
        record_login_failure(throttle_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    clear_login_failures(throttle_key)
    token = create_session(db, user.id)
    return schemas.LoginResponse(token=token, user=user_out(user))


@app.post("/api/auth/logout", status_code=204)
def logout(token: str = Depends(bearer_token), db: Session = Depends(get_db)):
    revoke_session(db, token)
    return Response(status_code=204)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "demo_mode": config.SEED_DEMO_DATA}


@app.get("/api/me", response_model=schemas.UserOut)
def get_me(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Idempotent per calendar day - safe on every poll (SmileMode fetches
    # this every few seconds).
    engagement.touch_daily_streak(db, user)
    return user_out(user)


@app.get("/api/hr/verify")
def verify_hr(user: models.User = Depends(require_hr_admin)):
    """
    Used by the frontend's hidden Smiley-logo toggle. Returns 200 only if
    the *server* considers this session hr_admin; the frontend never
    trusts a locally-cached role for this decision.
    """
    return {"ok": True, "username": user.username}


# ---------------------------------------------------------------------------
# Employee-facing visibility settings
# ---------------------------------------------------------------------------
@app.patch("/api/me/visibility", response_model=schemas.UserOut)
def update_visibility(
    payload: schemas.VisibilityUpdateRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Toggle whether ONE metric shows up on the public peer leaderboard.

    This is the entire scope of what this endpoint does: it flips a row
    in metric_visibilities. It does not touch ActivityLog, does not touch
    is_disloyal, and is never consulted by the HR routes or the telemetry
    simulator. Hiding every metric hides you from peers, not from HR.
    """
    if payload.metric not in models.LEADERBOARD_METRICS:
        raise HTTPException(status_code=400, detail=f"Unknown metric '{payload.metric}'")

    row = (
        db.query(models.MetricVisibility)
        .filter(models.MetricVisibility.user_id == user.id, models.MetricVisibility.metric == payload.metric)
        .first()
    )
    if row is None:
        db.add(models.MetricVisibility(user_id=user.id, metric=payload.metric, is_public=payload.is_public))
    else:
        row.is_public = payload.is_public
    db.commit()
    db.refresh(user)
    return user_out(user)


# ---------------------------------------------------------------------------
# Public (peer) leaderboard - visibility-filtered
# ---------------------------------------------------------------------------
@app.get("/api/leaderboard/{metric}", response_model=list[schemas.LeaderboardEntry])
def get_leaderboard(metric: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    if metric not in models.LEADERBOARD_METRICS:
        raise HTTPException(status_code=400, detail=f"Unknown metric '{metric}'")

    hidden = (
        db.query(models.MetricVisibility.id)
        .filter(
            models.MetricVisibility.user_id == models.User.id,
            models.MetricVisibility.metric == metric,
            models.MetricVisibility.is_public.is_(False),
        )
        .exists()
    )
    rows = db.query(models.User).filter(models.User.role == "employee", ~hidden).all()

    entries = [
        schemas.LeaderboardEntry(
            username=u.username,
            value=getattr(u, metric),
            is_you=(u.id == user.id),
            kudos_received=u.kudos_received,
        )
        for u in rows
    ]
    entries.sort(key=lambda e: e.value, reverse=True)
    return entries


@app.post("/api/kudos/{username}", response_model=schemas.KudosResponse)
async def send_kudos(username: str, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Send a peer a lightweight "cheer". Purely social - it never touches
    is_disloyal, activity_logs, or anything an HR route reads. Capped at
    one per (giver, receiver) pair per rolling 24h so it can't be spammed
    into a fake popularity contest.
    """
    if username == user.username:
        raise HTTPException(status_code=400, detail="You can't cheer yourself.")

    target = db.query(models.User).filter(models.User.username == username, models.User.role == "employee").first()
    if target is None:
        raise HTTPException(status_code=404, detail="No such employee")

    if not engagement.can_send_kudos(db, user.id, target.id):
        raise HTTPException(status_code=429, detail=f"You already cheered {username} in the last 24 hours.")

    db.add(models.Kudos(from_user_id=user.id, to_user_id=target.id))
    target.kudos_received += 1
    user.kudos_given += 1
    db.commit()
    db.refresh(target)

    # So the cheer shows up live on everyone's leaderboard, not just after
    # their next unrelated poll.
    await leaderboard_manager.broadcast({"type": "leaderboard_tick"})
    return schemas.KudosResponse(to_username=target.username, kudos_received=target.kudos_received)


# ---------------------------------------------------------------------------
# Personal to-do list - every query below is scoped to the caller's own
# rows. There is no route anywhere in this file, hr_admin-gated or not,
# that reads another user's tasks.
# ---------------------------------------------------------------------------
@app.get("/api/tasks", response_model=list[schemas.TaskOut])
def get_tasks(user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (
        db.query(models.Task)
        .filter(models.Task.user_id == user.id)
        .order_by(models.Task.is_done, models.Task.created_at.desc())
        .all()
    )


@app.post("/api/tasks", response_model=schemas.TaskOut)
def create_task(
    payload: schemas.TaskCreateRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Task title can't be empty.")
    task = models.Task(user_id=user.id, title=title)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _owned_task(task_id: int, user: models.User, db: Session) -> models.Task:
    task = db.get(models.Task, task_id)
    if task is None or task.user_id != user.id:
        # Same 404 whether the task doesn't exist or belongs to someone
        # else - never confirm another user's task IDs exist.
        raise HTTPException(status_code=404, detail="No such task")
    return task


@app.patch("/api/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: int,
    payload: schemas.TaskUpdateRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = _owned_task(task_id, user, db)
    if payload.is_done != task.is_done:
        # tasks_completed is a real, denormalized leaderboard metric - keep
        # it in sync both ways so unchecking a task doesn't leave a phantom
        # point behind.
        user.tasks_completed += 1 if payload.is_done else -1
    task.is_done = payload.is_done
    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(task_id: int, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = _owned_task(task_id, user, db)
    if task.is_done:
        user.tasks_completed = max(0, user.tasks_completed - 1)
    db.delete(task)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Company announcements - hr_admin writes, any authenticated user reads.
# The deliberately public counterpart to the hidden monitoring routes.
# ---------------------------------------------------------------------------
@app.get("/api/announcements", response_model=list[schemas.AnnouncementOut])
def get_announcements(_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    posts = db.query(models.Announcement).order_by(models.Announcement.created_at.desc()).limit(50).all()
    return [
        schemas.AnnouncementOut(
            id=p.id, title=p.title, body=p.body, author_username=p.author.username, created_at=p.created_at
        )
        for p in posts
    ]


@app.post("/api/announcements", response_model=schemas.AnnouncementOut)
def create_announcement(
    payload: schemas.AnnouncementCreateRequest,
    admin: models.User = Depends(require_hr_admin),
    db: Session = Depends(get_db),
):
    title, body = payload.title.strip(), payload.body.strip()
    if not title or not body:
        raise HTTPException(status_code=400, detail="Title and body can't be empty.")
    post = models.Announcement(author_id=admin.id, title=title, body=body)
    db.add(post)
    db.commit()
    db.refresh(post)
    return schemas.AnnouncementOut(
        id=post.id, title=post.title, body=post.body, author_username=admin.username, created_at=post.created_at
    )


# ---------------------------------------------------------------------------
# HR / Predatory Mode routes - all gated by require_hr_admin
# ---------------------------------------------------------------------------
def _telemetry_out(log: models.ActivityLog) -> schemas.TelemetryLogOut:
    return schemas.TelemetryLogOut(
        id=log.id,
        username=log.user.username,
        timestamp=log.timestamp,
        raw_text=log.raw_text,
        matched_keyword=log.matched_keyword,
        is_flagged=log.is_flagged,
    )


@app.get("/api/hr/telemetry", response_model=list[schemas.TelemetryLogOut])
def get_telemetry(
    limit: int = Query(default=50, ge=1, le=200),
    flagged: bool = Query(default=False),
    _admin: models.User = Depends(require_hr_admin),
    db: Session = Depends(get_db),
):
    q = db.query(models.ActivityLog)
    if flagged:
        q = q.filter(models.ActivityLog.is_flagged.is_(True))
    logs = q.order_by(models.ActivityLog.timestamp.desc()).limit(limit).all()
    return [_telemetry_out(log) for log in logs]


@app.get("/api/hr/employees/{username}/activity", response_model=list[schemas.TelemetryLogOut])
def get_employee_activity(
    username: str,
    limit: int = Query(default=200, ge=1, le=1000),
    flagged: bool = Query(default=False),
    _admin: models.User = Depends(require_hr_admin),
    db: Session = Depends(get_db),
):
    """One person's full activity log, newest first - the 'pull everything they've done' view."""
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise HTTPException(status_code=404, detail="No such user")
    q = db.query(models.ActivityLog).filter(models.ActivityLog.user_id == user.id)
    if flagged:
        q = q.filter(models.ActivityLog.is_flagged.is_(True))
    logs = q.order_by(models.ActivityLog.timestamp.desc()).limit(limit).all()
    return [_telemetry_out(log) for log in logs]


@app.get("/api/hr/disloyalty-stats", response_model=list[schemas.DisloyaltyStat])
def get_disloyalty_stats(_admin: models.User = Depends(require_hr_admin), db: Session = Depends(get_db)):
    users = db.query(models.User).order_by(models.User.role, models.User.username).all()
    return [
        schemas.DisloyaltyStat(username=u.username, violation_count=u.disloyal_violation_count, is_disloyal=u.is_disloyal)
        for u in users
    ]


@app.get("/api/hr/employees", response_model=list[schemas.EmployeeHrView])
def get_employees(_admin: models.User = Depends(require_hr_admin), db: Session = Depends(get_db)):
    # Everyone is monitored, hr_admin included; employees sort before admins.
    users = db.query(models.User).order_by(models.User.role, models.User.username).all()
    return [
        schemas.EmployeeHrView(
            id=u.id,
            username=u.username,
            role=u.role,
            points=u.points,
            apm=u.apm,
            total_clicks=u.total_clicks,
            active_screen_time=u.active_screen_time,
            tasks_completed=u.tasks_completed,
            kudos_given=u.kudos_given,
            is_disloyal=u.is_disloyal,
            disloyal_violation_count=u.disloyal_violation_count,
            # HR sees this regardless - visibility only affects the peer view.
            hidden_metrics=[v.metric for v in u.visibilities if not v.is_public],
        )
        for u in users
    ]


@app.get("/api/hr/integrations/status")
def get_integrations_status(_admin: models.User = Depends(require_hr_admin)):
    """Whether real Slack alerting is wired up. Purely informational."""
    return {"slack_configured": notifications.slack_configured()}


# ---------------------------------------------------------------------------
# WebSockets. Rejected connections are accepted and then closed with 1008
# (policy violation) rather than refused at the handshake: a refused
# handshake surfaces in the browser as a generic 1006, indistinguishable
# from a network drop, and the frontend needs to tell "stop retrying, you're
# not authorized" apart from "the server blipped, reconnect".
# ---------------------------------------------------------------------------
async def _authorize_ws(ws: WebSocket, token: str, require_admin: bool) -> bool:
    db = SessionLocal()
    try:
        user = get_user_from_ws_token(token, db)
        allowed = user.role == "hr_admin" or not require_admin
    except HTTPException:
        allowed = False
    finally:
        db.close()

    await ws.accept()
    if not allowed:
        await ws.close(code=1008)
    return allowed


async def _hold_open(ws: WebSocket, manager: ConnectionManager) -> None:
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # clients never send anything meaningful; this just waits for disconnect
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)


@app.websocket("/ws/leaderboard")
async def ws_leaderboard(ws: WebSocket, token: str = Query(...)):
    if await _authorize_ws(ws, token, require_admin=False):
        await _hold_open(ws, leaderboard_manager)


@app.websocket("/ws/hr/feed")
async def ws_hr_feed(ws: WebSocket, token: str = Query(...)):
    if await _authorize_ws(ws, token, require_admin=True):
        await _hold_open(ws, hr_manager)


# ---------------------------------------------------------------------------
# Built frontend. Mounted last so every /api and /ws route above wins; in
# production this makes the whole product one process on one origin.
# ---------------------------------------------------------------------------
if (config.FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="frontend")
