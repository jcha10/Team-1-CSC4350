import io

from app import cli, models


def _run(monkeypatch, argv, stdin=""):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    return cli.main(argv)


def test_create_user_and_login(client, monkeypatch):
    assert _run(monkeypatch, ["create-user", "zoe", "--role", "hr_admin", "--password-stdin"], "a-long-password\n") == 0
    r = client.post("/api/auth/login", json={"username": "zoe", "password": "a-long-password"})
    assert r.status_code == 200 and r.json()["user"]["role"] == "hr_admin"


def test_create_user_validation(client, monkeypatch):
    assert _run(monkeypatch, ["create-user", "zoe", "--password-stdin"], "short\n") == 1
    assert _run(monkeypatch, ["create-user", "no spaces!", "--password-stdin"], "a-long-password\n") == 1
    assert _run(monkeypatch, ["create-user", "zoe", "--password-stdin"], "a-long-password\n") == 0
    assert _run(monkeypatch, ["create-user", "zoe", "--password-stdin"], "a-long-password\n") == 1  # duplicate


def test_reset_password_revokes_sessions(client, monkeypatch, db):
    _run(monkeypatch, ["create-user", "zoe", "--password-stdin"], "old-password-1\n")
    token = client.post("/api/auth/login", json={"username": "zoe", "password": "old-password-1"}).json()["token"]

    assert _run(monkeypatch, ["reset-password", "zoe", "--password-stdin"], "new-password-2\n") == 0
    assert client.get("/api/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert db.query(models.AuthSession).count() == 0
    ok = client.post("/api/auth/login", json={"username": "zoe", "password": "new-password-2"})
    assert ok.status_code == 200


def test_list_users_prints_every_account_with_its_role(client, monkeypatch, capsys):
    _run(monkeypatch, ["create-user", "zoe", "--role", "hr_admin", "--password-stdin"], "a-long-password\n")
    _run(monkeypatch, ["create-user", "sam", "--password-stdin"], "a-long-password\n")
    capsys.readouterr()  # ignore the "Created ..." lines

    assert _run(monkeypatch, ["list-users"]) == 0
    rows = [line.split() for line in capsys.readouterr().out.strip().splitlines()]
    assert rows == [["sam", "employee"], ["zoe", "hr_admin"]]  # sorted by username
