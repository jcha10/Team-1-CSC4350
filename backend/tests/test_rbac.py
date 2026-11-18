import pytest
from starlette.websockets import WebSocketDisconnect

HR_GET_ROUTES = [
    "/api/hr/verify",
    "/api/hr/telemetry",
    "/api/hr/disloyalty-stats",
    "/api/hr/employees",
    "/api/hr/integrations/status",
]


@pytest.mark.parametrize("path", HR_GET_ROUTES)
def test_employee_gets_403_on_every_hr_route(client, make_user, login, path):
    make_user("alice")
    assert client.get(path, headers=login("alice")).status_code == 403


@pytest.mark.parametrize("path", HR_GET_ROUTES)
def test_hr_admin_gets_200_on_every_hr_route(client, make_user, login, path):
    make_user("boss", role="hr_admin")
    assert client.get(path, headers=login("boss")).status_code == 200


def test_only_hr_admin_can_post_announcements(client, make_user, login):
    make_user("alice")
    make_user("boss", role="hr_admin")
    body = {"title": "Hi", "body": "Hello all"}
    assert client.post("/api/announcements", json=body, headers=login("alice")).status_code == 403
    assert client.post("/api/announcements", json=body, headers=login("boss")).status_code == 200
    # ...and everyone can read it.
    posts = client.get("/api/announcements", headers=login("alice")).json()
    assert [p["title"] for p in posts] == ["Hi"]


def _token(headers):
    return headers["Authorization"].removeprefix("Bearer ")


def test_hr_feed_websocket_closes_1008_for_employee(client, make_user, login):
    make_user("alice")
    with client.websocket_connect(f"/ws/hr/feed?token={_token(login('alice'))}") as ws:
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_text()
    assert exc.value.code == 1008


def test_websockets_close_1008_for_bad_token(client):
    for path in ("/ws/hr/feed", "/ws/leaderboard"):
        with client.websocket_connect(f"{path}?token=garbage") as ws:
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_text()
        assert exc.value.code == 1008


def test_hr_feed_websocket_stays_open_for_admin(client, make_user, login):
    make_user("boss", role="hr_admin")
    with client.websocket_connect(f"/ws/hr/feed?token={_token(login('boss'))}") as ws:
        ws.send_text("ping")  # would raise if the server had closed the socket
