"""
Telemetry simulation + restricted-keyword parsing.

This is the mandatory, non-opt-outable monitoring pipeline. It has no
awareness of MetricVisibility at all - it writes ActivityLog rows and
updates User.is_disloyal / disloyal_violation_count for every employee,
every tick, regardless of what that employee has chosen to show on the
public leaderboard. Visibility settings live entirely in the leaderboard
query layer (see main.py); this module never imports or checks them.
"""
import asyncio
import random
import re

from sqlalchemy.orm import Session

from . import models

# Restricted keywords/phrases HR wants flagged. Matching is case-insensitive
# substring search over the simulated activity text.
RESTRICTED_KEYWORDS = [
    "job search",
    "indeed.com",
    "linkedin.com/jobs",
    "steam",
    "resume",
    "glassdoor",
    "ziprecruiter",
    "we're hiring",
    "new job",
]

# Simulated pool of "normal" (non-violating) activity strings.
BENIGN_ACTIVITY = [
    "Opened Salesforce dashboard",
    "Replied to Slack thread in #general",
    "Reviewed Jira ticket ENG-{n}",
    "Edited quarterly report in Google Sheets",
    "Joined Zoom standup",
    "Pushed commit to internal repo",
    "Read company wiki page 'Onboarding'",
    "Responded to email in Outlook",
    "Updated Confluence page",
    "Reviewed pull request #{n}",
]

# Simulated pool of activity strings that WILL trip a keyword match.
VIOLATION_ACTIVITY = [
    "Browsing indeed.com for 'Senior Engineer' roles",
    "Searching LinkedIn.com/jobs for openings",
    "Opened Steam store page - Baldur's Gate 3",
    "Updating resume in Google Docs",
    "Checking Glassdoor reviews for competitor",
    "Searching ZipRecruiter - remote positions",
    "Read article: 'signs it's time for a job search'",
    "Viewed 'we're hiring' post on a rival's careers page",
]


def scan_activity(text: str) -> str | None:
    """Return the first restricted keyword found in `text`, or None."""
    lowered = text.lower()
    for keyword in RESTRICTED_KEYWORDS:
        if keyword in lowered:
            return keyword
    return None


def _random_activity_text() -> str:
    # ~1 in 6 simulated events is a policy violation - frequent enough to
    # see the HR dashboard populate quickly in a demo.
    pool = VIOLATION_ACTIVITY if random.random() < (1 / 6) else BENIGN_ACTIVITY
    template = random.choice(pool)
    return template.format(n=random.randint(100, 999))


def generate_event_for_user(db: Session, user: models.User) -> dict:
    """
    Create one simulated activity event for `user`, update their gamified
    metrics, and - if it matches a restricted keyword - flag them for HR.
    Always runs; never consults MetricVisibility.

    Returns a plain dict snapshot, not the ORM ActivityLog/User objects.
    The caller processes multiple users on one shared session, and each
    user's commit() expires every other already-loaded instance in that
    session (SQLAlchemy's default expire_on_commit) - by the time the
    caller closes the session and gets around to reading, say, the first
    user's log object, its attributes are expired with no session left to
    reload them from, raising DetachedInstanceError. Snapshotting to a
    dict here, while the session is still open, sidesteps that entirely.
    """
    text = _random_activity_text()
    matched = scan_activity(text)

    # Gamified metrics drift upward each tick, as if the employee is
    # actively using the platform.
    user.points += random.randint(1, 15)
    user.apm = round(max(0.0, user.apm + random.uniform(-2, 6)), 1)
    user.total_clicks += random.randint(1, 25)
    user.active_screen_time = round(user.active_screen_time + random.uniform(0.1, 1.0), 1)

    log = models.ActivityLog(
        user_id=user.id,
        raw_text=text,
        matched_keyword=matched,
        is_flagged=matched is not None,
    )

    if matched:
        user.is_disloyal = True
        user.disloyal_violation_count += 1

    db.add(log)
    db.add(user)
    db.commit()
    db.refresh(log)

    return {
        "username": user.username,
        "raw_text": log.raw_text,
        "matched_keyword": log.matched_keyword,
        "is_flagged": log.is_flagged,
        "timestamp": log.timestamp.isoformat(),
        "violation_count": user.disloyal_violation_count,
    }


async def run_simulator(session_factory, broadcast_hr, broadcast_leaderboard, interval_seconds: float = 4.0):
    """
    Background loop: every `interval_seconds`, generate one simulated
    activity event for each employee, persist it, and broadcast the
    results to connected websocket clients.

    `broadcast_hr` receives every event's full detail (raw text, matched
    keyword) - this feed is never filtered by visibility settings.
    `broadcast_leaderboard` is called after the tick so leaderboard
    subscribers get refreshed (and visibility-filtered) standings.
    """
    while True:
        await asyncio.sleep(interval_seconds)
        db = session_factory()
        try:
            # Track every account, including hr_admin - the monitoring
            # pipeline watches everyone; role only governs who may *view*
            # the HR dashboard, not who is watched.
            users = db.query(models.User).all()
            events = [generate_event_for_user(db, user) for user in users]
        finally:
            db.close()

        for event in events:
            await broadcast_hr(
                {
                    "type": "activity",
                    "username": event["username"],
                    "raw_text": event["raw_text"],
                    "matched_keyword": event["matched_keyword"],
                    "is_flagged": event["is_flagged"],
                    "timestamp": event["timestamp"],
                }
            )

        await broadcast_leaderboard({"type": "leaderboard_tick"})
