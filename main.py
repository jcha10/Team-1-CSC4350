"""
FastAPI application entrypoint.

Route map:
  POST /api/auth/login                  -> exchange credentials for a bearer token (throttled)
  POST /api/auth/logout                 -> revoke the caller's session server-side
  GET  /api/health                      -> liveness + DB check; reports whether demo mode is on
  GET  /api/me                          -> current user's own profile
  GET  /api/hr/verify                   -> 200 iff caller is hr_admin, used by the hidden mode-switch
  GET  /*                               -> the built React app (when frontend/dist exists)

RBAC in one sentence: /api/hr/verify depends on `require_hr_admin` (see
auth.py), which raises 403 unless the role stored in the database is
"hr_admin".
"""
import contextlib
import logging

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import config, models, schemas
from .auth import (
    authenticate,
    bearer_token,
    clear_login_failures,
    create_session,
    ensure_login_allowed,
    get_current_user,
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
# App lifecycle: create tables, optional demo seed
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

    yield


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
    """Serialize a user for API responses."""
    return schemas.UserOut.model_validate(user)


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
# Built frontend. Mounted last so every /api and /ws route above wins; in
# production this makes the whole product one process on one origin.
# ---------------------------------------------------------------------------
if (config.FRONTEND_DIST / "index.html").exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIST, html=True), name="frontend")
