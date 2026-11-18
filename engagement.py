"""
Employee-facing engagement mechanics: daily login streaks and peer kudos.

Both are purely cosmetic/social - neither is read by any hr_admin route,
neither affects is_disloyal, and neither is gated by metric_visibilities
(they aren't leaderboard metrics, just extra texture on top of one).
"""
import datetime

from sqlalchemy.orm import Session

from . import models


def touch_daily_streak(db: Session, user: models.User) -> None:
    """
    Updates `user`'s streak counters based on today's date vs. the last
    date this ran for them. Idempotent within a single calendar day, so
    it's safe to call on every /api/me request (SmileMode polls that every
    few seconds) without the streak incrementing more than once per day.
    """
    today = datetime.date.today()

    if user.last_active_date == today:
        return  # already counted today

    if user.last_active_date == today - datetime.timedelta(days=1):
        user.current_streak += 1  # consecutive day
    else:
        user.current_streak = 1  # gap in visits (or first-ever visit) - streak restarts

    user.longest_streak = max(user.longest_streak, user.current_streak)
    user.last_active_date = today
    db.add(user)
    db.commit()
    db.refresh(user)


KUDOS_COOLDOWN = datetime.timedelta(hours=24)


def can_send_kudos(db: Session, from_user_id: int, to_user_id: int) -> bool:
    """One cheer per (giver, receiver) pair per rolling 24h window."""
    cutoff = datetime.datetime.utcnow() - KUDOS_COOLDOWN
    existing = (
        db.query(models.Kudos)
        .filter(
            models.Kudos.from_user_id == from_user_id,
            models.Kudos.to_user_id == to_user_id,
            models.Kudos.created_at >= cutoff,
        )
        .first()
    )
    return existing is None
