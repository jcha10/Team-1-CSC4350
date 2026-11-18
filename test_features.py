import datetime

from app import engagement, models


def _names(rows):
    return [r["username"] for r in rows]


# --- Visibility vs. monitoring ---------------------------------------------
def test_hiding_a_metric_removes_you_from_that_leaderboard_only(client, make_user, login):
    make_user("alice")
    make_user("bob")
    make_user("boss", role="hr_admin")
    alice = login("alice")

    client.patch("/api/me/visibility", json={"metric": "apm", "is_public": False}, headers=alice)

    assert "alice" not in _names(client.get("/api/leaderboard/apm", headers=alice).json())
    assert "alice" in _names(client.get("/api/leaderboard/points", headers=alice).json())

    # HR still sees her, and sees exactly what she hid.
    hr_rows = {e["username"]: e for e in client.get("/api/hr/employees", headers=login("boss")).json()}
    assert hr_rows["alice"]["hidden_metrics"] == ["apm"]


def test_new_accounts_default_to_public_on_every_metric(client, make_user, login):
    make_user("alice")
    me = client.get("/api/me", headers=login("alice")).json()
    assert len(me["visibilities"]) == len(models.LEADERBOARD_METRICS)
    assert all(v["is_public"] for v in me["visibilities"])


def test_hr_admins_never_appear_on_the_employee_leaderboard(client, make_user, login):
    make_user("alice")
    make_user("boss", role="hr_admin")
    assert _names(client.get("/api/leaderboard/points", headers=login("alice")).json()) == ["alice"]


def test_hr_admin_is_included_in_monitoring_views(client, make_user, login):
    make_user("alice")
    make_user("boss", role="hr_admin")
    rows = {e["username"]: e for e in client.get("/api/hr/employees", headers=login("boss")).json()}
    assert "boss" in rows and rows["boss"]["role"] == "hr_admin"
    stat_names = {s["username"] for s in client.get("/api/hr/disloyalty-stats", headers=login("boss")).json()}
    assert {"alice", "boss"} <= stat_names


def test_full_activity_pull(client, make_user, login, db):
    from app import models, telemetry

    make_user("alice")
    make_user("boss", role="hr_admin")
    alice = db.query(models.User).filter_by(username="alice").one()
    for _ in range(3):
        db.add(models.ActivityLog(user_id=alice.id, raw_text="Browsing indeed.com", matched_keyword="indeed.com", is_flagged=True))
        db.add(models.ActivityLog(user_id=alice.id, raw_text="Read wiki", matched_keyword=None, is_flagged=False))
    db.commit()

    boss = login("boss")
    everything = client.get("/api/hr/employees/alice/activity", headers=boss).json()
    assert len(everything) == 6
    flagged = client.get("/api/hr/employees/alice/activity?flagged=true", headers=boss).json()
    assert len(flagged) == 3 and all(a["is_flagged"] for a in flagged)
    assert client.get("/api/hr/employees/ghost/activity", headers=boss).status_code == 404
    # employees can't pull anyone's activity
    assert client.get("/api/hr/employees/alice/activity", headers=login("alice")).status_code == 403


def test_unknown_metric_is_400(client, make_user, login):
    make_user("alice")
    assert client.get("/api/leaderboard/salary", headers=login("alice")).status_code == 400


# --- Tasks -----------------------------------------------------------------
def test_tasks_are_private_to_their_owner(client, make_user, login):
    make_user("alice")
    make_user("bob")
    make_user("boss", role="hr_admin")
    alice, bob, boss = login("alice"), login("bob"), login("boss")

    task_id = client.post("/api/tasks", json={"title": "secret plan"}, headers=alice).json()["id"]

    assert client.get("/api/tasks", headers=bob).json() == []
    assert client.get("/api/tasks", headers=boss).json() == []
    for headers in (bob, boss):
        assert client.patch(f"/api/tasks/{task_id}", json={"is_done": True}, headers=headers).status_code == 404
        assert client.delete(f"/api/tasks/{task_id}", headers=headers).status_code == 404
    assert len(client.get("/api/tasks", headers=alice).json()) == 1


def test_tasks_completed_counter_tracks_both_directions(client, make_user, login):
    make_user("alice")
    alice = login("alice")

    def completed():
        return client.get("/api/me", headers=alice).json()["tasks_completed"]

    tid = client.post("/api/tasks", json={"title": "ship it"}, headers=alice).json()["id"]
    client.patch(f"/api/tasks/{tid}", json={"is_done": True}, headers=alice)
    client.patch(f"/api/tasks/{tid}", json={"is_done": True}, headers=alice)  # no-op, not a double count
    assert completed() == 1
    client.patch(f"/api/tasks/{tid}", json={"is_done": False}, headers=alice)
    assert completed() == 0
    client.patch(f"/api/tasks/{tid}", json={"is_done": True}, headers=alice)
    assert client.delete(f"/api/tasks/{tid}", headers=alice).status_code == 204
    assert completed() == 0


def test_blank_task_title_rejected(client, make_user, login):
    make_user("alice")
    assert client.post("/api/tasks", json={"title": "   "}, headers=login("alice")).status_code == 400


# --- Kudos -----------------------------------------------------------------
def test_kudos_rules_and_counters(client, make_user, login):
    make_user("alice")
    make_user("bob")
    make_user("boss", role="hr_admin")
    alice = login("alice")

    assert client.post("/api/kudos/alice", headers=alice).status_code == 400  # self
    assert client.post("/api/kudos/boss", headers=alice).status_code == 404  # not an employee
    assert client.post("/api/kudos/bob", headers=alice).json()["kudos_received"] == 1
    assert client.post("/api/kudos/bob", headers=alice).status_code == 429  # 24h cap

    assert client.get("/api/me", headers=alice).json()["kudos_given"] == 1
    assert client.get("/api/me", headers=login("bob")).json()["kudos_received"] == 1


# --- Streaks ---------------------------------------------------------------
def test_daily_streak_logic(client, make_user, db):
    make_user("alice")
    user = db.query(models.User).filter_by(username="alice").one()
    today = datetime.date.today()

    engagement.touch_daily_streak(db, user)
    assert user.current_streak == 1
    engagement.touch_daily_streak(db, user)  # same day: idempotent
    assert user.current_streak == 1

    user.last_active_date = today - datetime.timedelta(days=1)
    engagement.touch_daily_streak(db, user)
    assert (user.current_streak, user.longest_streak) == (2, 2)

    user.last_active_date = today - datetime.timedelta(days=3)
    engagement.touch_daily_streak(db, user)
    assert (user.current_streak, user.longest_streak) == (1, 2)
