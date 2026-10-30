import asyncio

from app import models, telemetry
from app.database import SessionLocal


def test_scan_activity_is_case_insensitive():
    assert telemetry.scan_activity("Opened STEAM store page") == "steam"
    assert telemetry.scan_activity("Browsing Indeed.com listings") == "indeed.com"
    assert telemetry.scan_activity("Reviewed Jira ticket ENG-101") is None


def test_violation_flags_user_even_when_every_metric_is_hidden(client, make_user, db, monkeypatch):
    make_user("alice")
    user = db.query(models.User).filter_by(username="alice").one()
    for metric in models.LEADERBOARD_METRICS:
        db.add(models.MetricVisibility(user_id=user.id, metric=metric, is_public=False))
    db.commit()

    monkeypatch.setattr(telemetry, "_random_activity_text", lambda: "Updating resume in Google Docs")
    event = telemetry.generate_event_for_user(db, user)

    assert event["is_flagged"] and event["matched_keyword"] == "resume"
    db.refresh(user)
    assert user.is_disloyal and user.disloyal_violation_count == 1


def test_simulator_keeps_ticking_with_multiple_employees(client, make_user, monkeypatch):
    """
    Regression test: per-user commits on a shared session used to expire
    earlier users' ORM objects, and reading them after the session closed
    raised DetachedInstanceError - silently killing the simulator after
    its first tick.
    """
    for name in ("alice", "bob", "carol"):
        make_user(name)
    monkeypatch.setattr(telemetry, "_random_activity_text", lambda: "Browsing indeed.com")

    hr_messages, ticks = [], []

    async def broadcast_hr(msg):
        hr_messages.append(msg)

    async def broadcast_leaderboard(msg):
        ticks.append(msg)

    async def run_two_ticks():
        task = asyncio.create_task(
            telemetry.run_simulator(SessionLocal, broadcast_hr, broadcast_leaderboard, interval_seconds=0.01)
        )
        while len(ticks) < 2:
            await asyncio.sleep(0.01)
            assert not task.done(), task.exception()
        task.cancel()

    asyncio.run(asyncio.wait_for(run_two_ticks(), timeout=10))

    assert len(ticks) >= 2
    assert {m["username"] for m in hr_messages} == {"alice", "bob", "carol"}
    assert all(m["is_flagged"] for m in hr_messages)
