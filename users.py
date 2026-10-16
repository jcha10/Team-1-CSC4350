"""Account creation/maintenance, shared by demo seeding and the admin CLI."""
import re

from sqlalchemy.orm import Session

from . import models
from .auth import hash_password

ROLES = ("employee", "hr_admin")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt ignores everything past 72 bytes


class UserError(ValueError):
    pass


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise UserError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise UserError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes.")


def create_user(db: Session, username: str, password: str, role: str = "employee") -> models.User:
    if not USERNAME_RE.match(username):
        raise UserError("Username must be 3-32 characters: letters, digits, '.', '_' or '-'.")
    if role not in ROLES:
        raise UserError(f"Role must be one of: {', '.join(ROLES)}.")
    validate_password(password)
    if db.query(models.User).filter(models.User.username == username).first():
        raise UserError(f"User '{username}' already exists.")

    user = models.User(username=username, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def reset_password(db: Session, username: str, password: str) -> models.User:
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise UserError(f"No such user '{username}'.")
    validate_password(password)
    user.password_hash = hash_password(password)
    # A password reset should kick out every existing login for that account.
    db.query(models.AuthSession).filter(models.AuthSession.user_id == user.id).delete()
    db.commit()
    return user
