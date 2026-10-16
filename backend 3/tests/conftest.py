"""Shared pytest fixtures for the API test suite

Every test runs against a throwaway SQLite database with background jobs
Demo data and Slack notifications switched off so that the tests are isolated, deterministic and never reach the network.
"""

import os
import tempfile

# Must be set before anything imports app.config / app.database
# The app reads its settings at import time
# Environment variableshave to exist before the `from app ...` imports further down run
_tmpdir = tempfile.mkdtemp(prefix="smiley-tests-")
# file backed DB in a temp dir
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"  
# no background simulator writing rows
os.environ["SIMULATOR_ENABLED"] = "false"  
# start from empty tables
os.environ["SEED_DEMO_DATA"] = "false"
# never post to Slack from tests
os.environ["SLACK_WEBHOOK_URL"] = ""  

# These imports come after the environment setup
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import auth  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.users import create_user  # noqa: E402

# Shared password for every user created through `make_user`
# Test can log in without passing a password around
PASSWORD = "correct-horse-battery"


@pytest.fixture()
def db():
    """A database session for tests to inspect or modify rows directly

    Changes made here must be committed before the app can see them.
    """
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client():
    """A TestClient against a freshly reset database

    Drops and recreates every table so each test starts from an empty schema
    Clears the in memory failed login counter
    Lockouts from one test can't leak into the next
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    auth._failed_logins.clear()
    # Using the client as a context manager runs the app's startup and shutdown
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def make_user(client, db):
    """Call `make_user("name", role=...)` to create a user

    Depends on `client` so the tables are reset and recreated before any user is inserted
    Users get the shared PASSWORD and default to the "employee" role
    Returns the username for convenience
    """

    def _make(username, role="employee"):
        create_user(db, username, PASSWORD, role)
        return username

    return _make


@pytest.fixture()
def login(client):
    """Call `login("name")` to get auth headers for that user

    Logs in through the real /api/auth/login endpoint and returns a headers ready to pass to `client.get(..., headers=...)`
    Fails the test immediately (showing the response body) if the login is rejected
    """

    def _login(username, password=PASSWORD):
        r = client.post("/api/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}

    return _login
