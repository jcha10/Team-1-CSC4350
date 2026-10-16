"""
Database schema (SQLAlchemy ORM models -> SQLite tables).

- users:          identity and role.
- auth_sessions:  one row per login. Only a hash of the token is stored.
"""
import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # "employee" or "hr_admin" - the single source of truth for RBAC checks.
    role = Column(String, nullable=False, default="employee")

    created_at = Column(DateTime, default=datetime.datetime.utcnow)


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
