"""
Database schema (SQLAlchemy ORM models -> SQLite tables).

Four tables:

- users:               identity, role, the live telemetry numbers HR cares
                        about (points/apm/clicks/active time, plus the
                        disloyalty flag + counter), and the employee-facing
                        engagement hooks (streak, kudos received).
- metric_visibilities:  ITEMIZED per-metric opt-in/opt-out for the *public*
                        peer leaderboard only. One row per (user, metric).
                        This table has zero effect on telemetry collection -
                        the simulator and HR routes never read it.
- activity_logs:        the raw simulated browsing/activity events, plus
                        whether they tripped a restricted-keyword match.
- kudos:                one row per peer "cheer" sent on the leaderboard -
                        a purely social, opt-in feature with no bearing on
                        anything HR sees.
- tasks:                a private per-user to-do list. Only ever queried
                        filtered by owner - nobody, including hr_admin,
                        has a route that reads another user's tasks.
- announcements:        company-wide posts. hr_admin can write, every
                        authenticated user (any role) can read - the one
                        table in this schema that's intentionally visible
                        both ways, unlike the monitoring tables above.
"""
import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
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
# The first four are simulated (driven by telemetry.py); the last two are
# real counts of actual actions taken in the app (completing a to-do,
# sending a kudos) - both kinds go through the identical visibility system.
LEADERBOARD_METRICS = [
    "points",
    "apm",
    "total_clicks",
    "active_screen_time",
    "tasks_completed",
    "kudos_given",
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

    # --- Employee-facing engagement hooks. Purely cosmetic/social - HR
    # routes never read these, and they never affect is_disloyal. ---
    current_streak = Column(Integer, default=0, nullable=False)  # consecutive days visited
    longest_streak = Column(Integer, default=0, nullable=False)
    last_active_date = Column(Date, nullable=True)  # last calendar day touch_daily_streak() ran for
    kudos_received = Column(Integer, default=0, nullable=False)  # denormalized count, see Kudos table
    kudos_given = Column(Integer, default=0, nullable=False)  # denormalized count, see Kudos table
    tasks_completed = Column(Integer, default=0, nullable=False)  # denormalized count, see Task table

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


class Kudos(Base):
    """
    One row per peer "cheer" sent from the leaderboard. Capped at one per
    (from_user, to_user) per calendar day at the route level (main.py) -
    the table itself has no unique constraint enforcing that so the app
    can decide the exact dedup window in one place.
    """
    __tablename__ = "kudos"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class Task(Base):
    """
    A private to-do item. Every route that touches this table filters by
    `user_id == <the authenticated caller>` - there is no route, including
    any hr_admin one, that lists another user's tasks.
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    is_done = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Announcement(Base):
    """
    A company-wide post. Written only by hr_admin (enforced at the route
    level), readable by any authenticated user regardless of role - the
    deliberately public counterpart to the hidden monitoring tables above.
    """
    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    body = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    author = relationship("User")


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
