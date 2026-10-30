"""Tests for the peer leaderboard and its per-metric visibility settings."""


def _names(entries):
    return [e["username"] for e in entries]


def test_hiding_a_metric_only_hides_that_leaderboard(client, make_user, login):
    make_user("alice")
    make_user("bob")
    alice, bob = login("alice"), login("bob")

    r = client.patch("/api/me/visibility", json={"metric": "apm", "is_public": False}, headers=alice)
    assert r.status_code == 200

    # Bob no longer sees alice on the APM leaderboard...
    assert "alice" not in _names(client.get("/api/leaderboard/apm", headers=bob).json())
    # ...but she is still on every other leaderboard.
    assert "alice" in _names(client.get("/api/leaderboard/points", headers=bob).json())
