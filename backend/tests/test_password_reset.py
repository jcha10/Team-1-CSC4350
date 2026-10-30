"""Tests for password reset and session invalidation (app/users.py)

Covers:
- Password reset functionality (updating password hash)
- Handling of nonexistent users
- Password validation during reset
- Session revocation (invalidating tokens of the target user)
- Isolation of session revocation (other active users remain logged in)
- Post-reset login verification
"""

import pytest

from app import auth, models
from app.users import UserError, create_user, reset_password


def test_reset_password_success(client, db):
    """reset_password updates user's password hash and verifies with new password."""
    user = create_user(db, "reset_user", "old_password123")
    old_hash = user.password_hash

    updated_user = reset_password(db, "reset_user", "new_password456")
    assert updated_user.id == user.id
    assert updated_user.password_hash != old_hash
    assert auth.verify_password("new_password456", updated_user.password_hash)
    assert not auth.verify_password("old_password123", updated_user.password_hash)


def test_reset_password_nonexistent_user(client, db):
    """Attempting to reset password for a nonexistent user raises UserError."""
    with pytest.raises(UserError, match="No such user 'ghost'."):
        reset_password(db, "ghost", "new_password123")


def test_reset_password_invalid_password_too_short(client, db):
    """Too short new password raises UserError and leaves old password unchanged."""
    user = create_user(db, "reset_user", "old_password123")
    old_hash = user.password_hash

    with pytest.raises(UserError, match="Password must be at least"):
        reset_password(db, "reset_user", "short")

    db.refresh(user)
    assert user.password_hash == old_hash
    assert auth.verify_password("old_password123", user.password_hash)


def test_reset_password_invalid_password_too_long(client, db):
    """New password exceeding byte limit raises UserError and leaves old password unchanged."""
    user = create_user(db, "reset_user_long", "old_password123")
    old_hash = user.password_hash

    with pytest.raises(UserError, match="Password must be at most"):
        reset_password(db, "reset_user_long", "a" * 73)

    db.refresh(user)
    assert user.password_hash == old_hash
    assert auth.verify_password("old_password123", user.password_hash)


def test_reset_password_revokes_target_user_sessions(client, db):
    """reset_password deletes all active auth sessions for the target user."""
    create_user(db, "alice", "password123")

    # Log in through API to generate a session
    r = client.post("/api/auth/login", json={"username": "alice", "password": "password123"})
    assert r.status_code == 200
    token = r.json()["token"]

    # Verify token works
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    # Reset password
    reset_password(db, "alice", "new_password123")

    # Previous token is now revoked (401 Unauthorized)
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_reset_password_session_isolation(client, db):
    """reset_password only revokes sessions for the target user, preserving other users."""
    create_user(db, "alice", "password123")
    create_user(db, "bob", "password123")

    r_alice = client.post("/api/auth/login", json={"username": "alice", "password": "password123"})
    token_alice = r_alice.json()["token"]

    r_bob = client.post("/api/auth/login", json={"username": "bob", "password": "password123"})
    token_bob = r_bob.json()["token"]

    # Both tokens are valid initially
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token_alice}"}).status_code == 200
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token_bob}"}).status_code == 200

    # Reset alice's password
    reset_password(db, "alice", "new_password123")

    # Alice is kicked out, but Bob's session remains active
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token_alice}"}).status_code == 401
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token_bob}"}).status_code == 200


def test_reset_password_login_verification(client, db):
    """After password reset, logging in with old password fails while new password succeeds."""
    create_user(db, "charlie", "old_secret_123")
    reset_password(db, "charlie", "new_secret_456")

    # Old password fails
    bad_login = client.post("/api/auth/login", json={"username": "charlie", "password": "old_secret_123"})
    assert bad_login.status_code == 401

    # New password succeeds
    good_login = client.post("/api/auth/login", json={"username": "charlie", "password": "new_secret_456"})
    assert good_login.status_code == 200
    assert good_login.json()["user"]["username"] == "charlie"
