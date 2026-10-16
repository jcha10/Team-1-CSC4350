"""
Demo accounts for local development and classroom demos. Only runs when
SEED_DEMO_DATA=true (see config.py) - never enable it in production, where
accounts should be created with the CLI (`python -m app.cli create-user`).
"""
import logging

from sqlalchemy.orm import Session

from . import models
from .users import create_user

logger = logging.getLogger("smiley.seed")

DEMO_PASSWORD = "password123"

DEMO_USERS = [
    ("alice", "employee"),
    ("bob", "employee"),
    ("carol", "employee"),
    ("dave", "employee"),
    ("hr_admin", "hr_admin"),
]


def seed_if_empty(db: Session) -> None:
    if db.query(models.User).count() > 0:
        return
    for username, role in DEMO_USERS:
        create_user(db, username, DEMO_PASSWORD, role)
    logger.warning(
        "Seeded demo accounts (%s) with the shared password '%s'. Do not use SEED_DEMO_DATA in production.",
        ", ".join(u for u, _ in DEMO_USERS),
        DEMO_PASSWORD,
    )
