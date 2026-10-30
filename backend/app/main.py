"""
FastAPI application entrypoint.

Route map:
  POST /api/auth/login                  -> exchange credentials for a bearer token (throttled)
  POST /api/auth/logout                 -> revoke the caller's session server-side
  GET  /api/health                      -> liveness + DB check; reports whether demo mode is on
  GET  /api/me                          -> current user's own profile + visibility settings
  PATCH /api/me/visibility              -> toggle public leaderboard visibility for ONE metric
  GET  /api/leaderboard/{metric}        -> ranked list, excluding users who hid that metric
  GET  /api/hr/verify                   -> 200 iff caller is hr_admin, used by the hidden mode-switch
  WS   /ws/leaderboard?token=...        -> push notifications when leaderboard standings change
  GET  /*                               -> the built React app (when frontend/dist exists)

RBAC in one sentence: /api/hr/verify depends on `require_hr_admin` (see
auth.py), which raises 403 unless the role stored in the database is
"hr_admin".
"""
import asyncio
import contextlib
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import config, models, schemas, telemetry
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

# Without this, our own INFO-level log lines are silently dropped - the
# root logger defaults to WARNING with no handler, and uvicorn only
# configures its own "uvicorn.*" loggers.
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
        )
        for u in rows
    ]
    entries.sort(key=lambda e: e.value, reverse=True)
    return entries


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


# ---------------------------------------------------------------------------
# Built frontend. Mounted last so every /api and /ws route above wins; in
# production this makes the whole product one process on one origin.
# ---------------------------------------------------------------------------
if (config.FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="frontend")

