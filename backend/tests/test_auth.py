"""Tests for login, logout, session tokens, and related security"""

import datetime

from app import models


def test_login_success_and_generic_failure(client, make_user):
    """Valid credentials log in; invalid ones fail without leaking which part was wrong."""
    make_user("alice")
    ok = client.post("/api/auth/login", json={"username": "alice", "password": "correct-horse-battery"})
    assert ok.status_code == 200
    assert ok.json()["user"]["username"] == "alice"

    # Wrong password for a real user v.s. a user that doesn't exist at all
    bad_pw = client.post("/api/auth/login", json={"username": "alice", "password": "nope"})
    no_user = client.post("/api/auth/login", json={"username": "ghost", "password": "nope"})
    assert bad_pw.status_code == no_user.status_code == 401
    # Same message while it doesn't reveal which usernames exist
    assert bad_pw.json() == no_user.json()


def test_missing_or_garbage_token_is_401(client):
    """Protected endpoints reject requests with no token or an invalid one"""
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_logout_revokes_token(client, make_user, login):
    """After logout the same token does not work"""
    make_user("alice")
    headers = login("alice")
    assert client.get("/api/me", headers=headers).status_code == 200  # token works before logout
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/me", headers=headers).status_code == 401  # and is rejected after


def test_expired_session_is_rejected(client, make_user, login, db):
    """A token with an expired session is refused"""
    make_user("alice")
    headers = login("alice")
    # Backdate every session to one second ago instead of waiting
    db.query(models.AuthSession).update({"expires_at": datetime.datetime.utcnow() - datetime.timedelta(seconds=1)})
    # Commit so the app's own DB session sees the change
    db.commit() 
    assert client.get("/api/me", headers=headers).status_code == 401


def test_only_token_hash_is_stored(client, make_user, db):
    """The raw session token is never written to the database and is only in the hash

    If the database leaks the stored values can't be replayed
    """
    make_user("alice")
    token = client.post("/api/auth/login", json={"username": "alice", "password": "correct-horse-battery"}).json()[
        "token"
    ]
    stored = [s.token_hash for s in db.query(models.AuthSession).all()]
    #None of the stored values is the raw token
    assert stored and token not in stored


def test_lockout_after_repeated_failures(client, make_user):
    """Five wrong passwords in a row lock the account"""
    make_user("alice")
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "alice", "password": "wrong"}).status_code == 401
    # Right password is also refused while locked out
    locked = client.post("/api/auth/login", json={"username": "alice", "password": "correct-horse-battery"})
    # 429 Too Many Requests
    assert locked.status_code == 429  


def test_health_reports_demo_mode_off_by_default(client):
    """The health check is up and reports demo mode off"""
    assert client.get("/api/health").json() == {"status": "ok", "demo_mode": False}


def test_input_length_limits(client):
    """Long usernames are rejected by request validation before any auth run

    65 characters is one past the 64 character limit
    422 is FastAPI's validation-error status
    """
    assert client.post("/api/auth/login", json={"username": "x" * 65, "password": "p"}).status_code == 422
