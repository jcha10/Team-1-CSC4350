"""
Database schema (SQLAlchemy ORM models -> SQLite tables).

- users:               identity, role, the live telemetry numbers (points,
                        apm, clicks, active time) and the disloyalty flag +
                        counter.
- metric_visibilities:  ITEMIZED per-metric opt-in/opt-out for the *public*
                        peer leaderboard only. One row per (user, metric).
                        This table has zero effect on telemetry collection -
                        the simulator never reads it.
- activity_logs:        the raw simulated browsing/activity events, plus
                        whether they tripped a restricted-keyword match.
- auth_sessions:        one row per login. Only a hash of the token is
                        stored.
"""
import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base

# The set of metrics an employee can individually show/hide on the public
# leaderboard. Kept in one place so backend validation and seed data agree.
# All four are simulated (driven by telemetry.py).
LEADERBOARD_METRICS = [
    "points",
    "apm",
    "total_clicks",
    "active_screen_time",
]


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # "employee" or "hr_admin" - the single source of truth for RBAC checks.
    role = Column(String, nullable=False, default="employee")

    # --- Gamified telemetry (visible to the employee themselves always,
    # visible to peers only per-metric via metric_visibilities) ---
    points = Column(Integer, default=0, nullable=False)
    apm = Column(Float, default=0.0, nullable=False)  # actions per minute
    total_clicks = Column(Integer, default=0, nullable=False)
    active_screen_time = Column(Float, default=0.0, nullable=False)  # minutes

    # --- Hidden HR/security telemetry. Never gated by metric_visibilities,
    # never opt-outable from the employee UI, only ever reachable through
    # hr_admin-only routes. ---
    is_disloyal = Column(Boolean, default=False, nullable=False)
    disloyal_violation_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    visibilities = relationship(
        "MetricVisibility", back_populates="user", cascade="all, delete-orphan"
    )
    activity_logs = relationship(
        "ActivityLog", back_populates="user", cascade="all, delete-orphan"
    )


class MetricVisibility(Base):
    """
    Per-metric, per-user toggle for the PUBLIC leaderboard only.

    is_public=False means: this user's row is excluded from the
    peer-facing /api/leaderboard/{metric} response and the leaderboard
    websocket broadcast for that metric. It has no other effect - it is
    read in exactly one place in the whole backend (leaderboard queries).
    """
    __tablename__ = "metric_visibilities"
    __table_args__ = (UniqueConstraint("user_id", "metric", name="uq_user_metric"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    metric = Column(String, nullable=False)  # one of LEADERBOARD_METRICS
    is_public = Column(Boolean, default=True, nullable=False)

    user = relationship("User", back_populates="visibilities")


class ActivityLog(Base):
    """
    A single simulated activity event for a user, produced by the
    telemetry simulator (see telemetry.py). Always written regardless of
    that user's leaderboard visibility settings - this is the mandatory,
    non-opt-outable monitoring stream that only hr_admin routes expose.
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    raw_text = Column(String, nullable=False)
    matched_keyword = Column(String, nullable=True)
    is_flagged = Column(Boolean, default=False, nullable=False)

    user = relationship("User", back_populates="activity_logs")


class AuthSession(Base):
    """
    A login session. Only a SHA-256 hash of the bearer token is stored, so
    a copy of the database alone can't be used to impersonate anyone.
    Stored here rather than in process memory so sessions survive restarts
    and logout actually revokes the token server-side.
    """
    __tablename__ = "auth_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False, index=True)
