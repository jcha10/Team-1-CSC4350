import datetime

from app import models


def test_login_success_and_generic_failure(client, make_user):
    make_user("alice")
    ok = client.post("/api/auth/login", json={"username": "alice", "password": "correct-horse-battery"})
    assert ok.status_code == 200
    assert ok.json()["user"]["username"] == "alice"

    bad_pw = client.post("/api/auth/login", json={"username": "alice", "password": "nope"})
    no_user = client.post("/api/auth/login", json={"username": "ghost", "password": "nope"})
    assert bad_pw.status_code == no_user.status_code == 401
    # Same message either way - doesn't reveal which usernames exist.
    assert bad_pw.json() == no_user.json()


def test_missing_or_garbage_token_is_401(client):
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_logout_revokes_token(client, make_user, login):
    make_user("alice")
    headers = login("alice")
    assert client.get("/api/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/me", headers=headers).status_code == 401


def test_expired_session_is_rejected(client, make_user, login, db):
    make_user("alice")
    headers = login("alice")
    db.query(models.AuthSession).update({"expires_at": datetime.datetime.utcnow() - datetime.timedelta(seconds=1)})
    db.commit()
    assert client.get("/api/me", headers=headers).status_code == 401


def test_only_token_hash_is_stored(client, make_user, db):
    make_user("alice")
    token = client.post("/api/auth/login", json={"username": "alice", "password": "correct-horse-battery"}).json()[
        "token"
    ]
    stored = [s.token_hash for s in db.query(models.AuthSession).all()]
    assert stored and token not in stored


def test_lockout_after_repeated_failures(client, make_user):
    make_user("alice")
    for _ in range(5):
        assert client.post("/api/auth/login", json={"username": "alice", "password": "wrong"}).status_code == 401
    # Even the right password is refused while locked out.
    locked = client.post("/api/auth/login", json={"username": "alice", "password": "correct-horse-battery"})
    assert locked.status_code == 429


def test_health_reports_demo_mode_off_by_default(client):
    assert client.get("/api/health").json() == {"status": "ok", "demo_mode": False}


def test_input_length_limits(client, make_user, login):
    assert client.post("/api/auth/login", json={"username": "x" * 65, "password": "p"}).status_code == 422
    make_user("alice")
    headers = login("alice")
    assert client.post("/api/tasks", json={"title": "t" * 201}, headers=headers).status_code == 422
