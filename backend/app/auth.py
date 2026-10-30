"""
Authentication + Role-Based Access Control (RBAC).

Login exchanges a username/password for an opaque random bearer token.
Only the token's SHA-256 hash is persisted (auth_sessions table), with a
fixed expiry. Every authenticated request - REST via the
`Authorization: Bearer <token>` header, WebSocket via a `?token=` query
param since browsers can't set headers on the WS handshake - resolves the
hash back to a live, unexpired session and loads the user fresh from the
database.

The RBAC part is `require_hr_admin`: a FastAPI dependency that raises
403 unless the *stored* `user.role == "hr_admin"`. Every Predatory Mode
route goes through it, so there is exactly one place that decides "can
this caller see HR telemetry".
"""
import datetime
import hashlib
import secrets
import time

from fastapi import Depends, Header, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import config, models
from .database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Verified against when the username doesn't exist, so a failed login
# takes the same bcrypt time either way and response timing can't be used
# to discover which usernames are real.
_DUMMY_HASH = pwd_context.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def authenticate(db: Session, username: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    return user if verify_password(password, user.password_hash) else None


# ---------------------------------------------------------------------------
# Keyed by (client IP, username) so an attacker can't lock a victim out from a
# different IP.
# ---------------------------------------------------------------------------
_failed_logins: dict[tuple[str, str], list[float]] = {}


def _recent_failures(key: tuple[str, str]) -> list[float]:
    cutoff = time.monotonic() - config.LOGIN_LOCKOUT_MINUTES * 60
    recent = [t for t in _failed_logins.get(key, []) if t > cutoff]
    _failed_logins[key] = recent
    return recent


def ensure_login_allowed(key: tuple[str, str]) -> None:
    if len(_recent_failures(key)) >= config.LOGIN_MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again later.",
        )


def record_login_failure(key: tuple[str, str]) -> None:
    _recent_failures(key).append(time.monotonic())


def clear_login_failures(key: tuple[str, str]) -> None:
    _failed_logins.pop(key, None)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Session, user_id: int) -> str:
    now = datetime.datetime.utcnow()
    # deletes any expired sessions for this user, so the DB doesn't grow unbounded
    db.query(models.AuthSession).filter(models.AuthSession.expires_at < now).delete()
    # create a new session with a random token. only the hash is stored in the DB
    token = secrets.token_urlsafe(32)
    db.add(
        models.AuthSession(
            token_hash=_hash_token(token),
            user_id=user_id,
            expires_at=now + datetime.timedelta(hours=config.SESSION_TTL_HOURS),
        )
    )
    db.commit()
    return token


def revoke_session(db: Session, token: str) -> None:
    db.query(models.AuthSession).filter(models.AuthSession.token_hash == _hash_token(token)).delete()
    db.commit()


def _user_from_token(token: str, db: Session) -> models.User:
    session = db.query(models.AuthSession).filter(models.AuthSession.token_hash == _hash_token(token)).first()
    if session is None or session.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    # load the user fresh from the DB, so if the account was deleted or role changed, we see it instead of trusting the session's cached user data
    user = db.get(models.User, session.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    return authorization.removeprefix("Bearer ").strip()


def get_current_user(token: str = Depends(bearer_token), db: Session = Depends(get_db)) -> models.User:
    return _user_from_token(token, db)


def get_user_from_ws_token(token: str, db: Session) -> models.User:
    return _user_from_token(token, db)


def require_hr_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """
    The RBAC gate for every Predatory Mode route: 403 unless the role
    stored in the database - not anything the client claims - is hr_admin.
    """
    if user.role != "hr_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR-only resource. Your account does not have hr_admin privileges.",
        )
    return user
