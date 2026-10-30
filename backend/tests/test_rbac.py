import pytest
from starlette.websockets import WebSocketDisconnect

HR_GET_ROUTES = ["/api/hr/verify"]


@pytest.mark.parametrize("path", HR_GET_ROUTES)
def test_employee_gets_403_on_every_hr_route(client, make_user, login, path):
    make_user("alice")
    assert client.get(path, headers=login("alice")).status_code == 403


@pytest.mark.parametrize("path", HR_GET_ROUTES)
def test_hr_admin_gets_200_on_every_hr_route(client, make_user, login, path):
    make_user("boss", role="hr_admin")
    assert client.get(path, headers=login("boss")).status_code == 200


def test_websockets_close_1008_for_bad_token(client):
    for path in ("/ws/leaderboard",):
        with client.websocket_connect(f"{path}?token=garbage") as ws:
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_text()
        assert exc.value.code == 1008
