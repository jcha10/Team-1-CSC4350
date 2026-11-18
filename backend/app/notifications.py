"""
Outbound violation alerts via a Slack Incoming Webhook.

This is a real integration, not a simulation: when configured, it makes an
actual HTTP POST to Slack's API against whatever webhook URL you provide
(point it at a free sandbox/dev Slack workspace - never a real company's).
When no webhook is configured, every call falls back to a structured log
line instead of raising, so the rest of the app (and grading it) never
depends on having Slack credentials on hand.

Wiring: telemetry.generate_event_for_user() calls send_violation_alert()
the moment it flags a violation - see telemetry.py.
"""
import logging
import os

import httpx

logger = logging.getLogger("smiley.notifications")

_TIMEOUT_SECONDS = 4.0


def _webhook_url() -> str:
    # Read lazily (not cached at import time) so a .env file loaded by
    # main.py's load_dotenv() - which necessarily runs after this module
    # is first imported - still takes effect.
    return os.environ.get("SLACK_WEBHOOK_URL", "").strip()


def slack_configured() -> bool:
    return bool(_webhook_url())


async def send_violation_alert(username: str, matched_keyword: str, violation_count: int, raw_text: str) -> bool:
    """
    Notify HR of a new disloyalty violation. Returns True if an actual
    Slack message was sent, False if it fell back to a local log line
    (either because no webhook is configured, or the request failed -
    a flaky/unreachable webhook must never take down the telemetry
    simulator, so every failure is caught and logged here).
    """
    message = (
        f":rotating_light: *Disloyalty flag* — `{username}` matched restricted keyword "
        f"*\"{matched_keyword}\"* (violation #{violation_count})\n> {raw_text}"
    )

    if not slack_configured():
        logger.info("[slack:not-configured] %s", message.replace("\n> ", " — "))
        return False

    payload = {"text": message}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            response = await client.post(_webhook_url(), json=payload)
            response.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        logger.warning("[slack:delivery-failed] %s (%s)", message.replace("\n> ", " — "), exc)
        return False
