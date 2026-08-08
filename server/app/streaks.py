"""
streaks.py — The "leaving costs something" engine.

A streak = number of consecutive days you did something inside the zone.
  * If your last streak day was YESTERDAY  → streak + 1
  * If it was TODAY already               → no change (can't double-count)
  * If it was any earlier day             → streak resets to 1

Dates are UTC days (YYYY-MM-DD strings) so "day" means the same everywhere.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def today_key() -> str:
    """Today's date as "YYYY-MM-DD" (UTC)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def yesterday_key() -> str:
    """Yesterday's date as "YYYY-MM-DD" (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")


def register_streak_day(device) -> int:
    """Record "this device was active inside the zone today".

    Mutates the device's streak fields in place (caller saves the row).
    Returns the NEW streak value.
    """
    today = today_key()

    # Already counted today — leave it alone.
    if device.last_streak_day == today:
        return device.streak

    # Active yesterday → keep the flame alive.
    if device.last_streak_day == yesterday_key():
        device.streak += 1
    else:
        # Missed a day (or brand new) → restart at 1.
        device.streak = 1

    device.last_streak_day = today
    return device.streak
