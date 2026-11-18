"""Tests for Slack violation alerts. No real network calls are made."""
import asyncio
import logging

import httpx

from app import notifications


def _send_alert():
    return asyncio.run(notifications.send_violation_alert("alice", "steam", 1, "Opened Steam store page"))


def test_alert_without_a_slack_url_is_logged_instead(monkeypatch, caplog):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")
    with caplog.at_level(logging.INFO, logger="smiley.notifications"):
        assert _send_alert() is False
    assert "[slack:not-configured]" in caplog.text


def test_failed_slack_request_is_logged_not_raised(monkeypatch, caplog):
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.example/fake")

    async def unreachable(*args, **kwargs):
        raise httpx.ConnectError("Slack is unreachable")

    monkeypatch.setattr(httpx.AsyncClient, "post", unreachable)
    with caplog.at_level(logging.WARNING, logger="smiley.notifications"):
        assert _send_alert() is False
    assert "[slack:delivery-failed]" in caplog.text
