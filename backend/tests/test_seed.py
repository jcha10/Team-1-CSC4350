"""Tests for creating the demo accounts on an empty database."""
from app import models
from app.seed import DEMO_PASSWORD, DEMO_USERS, seed_if_empty


def test_seed_creates_demo_accounts_once(client, db):
    seed_if_empty(db)
    usernames = {u.username for u in db.query(models.User).all()}
    assert usernames == {name for name, _ in DEMO_USERS}

    # Running it again on a database that already has users adds nothing.
    seed_if_empty(db)
    assert db.query(models.User).count() == len(DEMO_USERS)

    # The seeded accounts can actually log in.
    r = client.post("/api/auth/login", json={"username": "alice", "password": DEMO_PASSWORD})
    assert r.status_code == 200
