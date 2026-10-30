"""WebSocket authentication tests.

The /ws/leaderboard endpoint must never let an unauthenticated caller
receive live leaderboard data.  Because browsers cannot attach an
Authorization header on a WebSocket handshake, the token is passed as a
query parameter instead.  The server accepts the HTTP upgrade regardless
(so the browser sees a clean 1008 close code rather than a raw TCP error
or an ambiguous 1006 "network drop") and then immediately closes the
socket with code 1008 (Policy Violation).

1008 is the deliberate choice: it means "stop retrying, you are not
authorised" rather than "something went wrong, please reconnect".
"""


def test_websocket_close_1008_for_bad_token(client):
    """A fake token must result in an immediate close with code 1008.

    Steps
    -----
    1. Open the WebSocket with an obviously invalid token string.
    2. Read the first frame back from the server — it must be a close
       frame (type 'websocket.close').
    3. Assert the close code is exactly 1008 (Policy Violation).
    """
    with client.websocket_connect("/ws/leaderboard?token=this-is-not-a-real-token") as ws:
        frame = ws.receive()

        assert frame.get("type") == "websocket.close", (
            f"Expected a websocket.close frame but got: {frame}"
        )
        assert frame.get("code") == 1008, (
            f"Expected close code 1008 (Policy Violation) for a bad token, "
            f"but got code {frame.get('code')!r}. Full frame: {frame}"
        )
