"""Release-week date ranges (ISO weeks, Monday through Sunday)."""

from datetime import date, timedelta

from django.utils import timezone


def release_week_bounds(week_offset: int = 0, today: date | None = None) -> tuple[date, date]:
    """Return the ``(monday, sunday)`` of the week ``week_offset`` weeks from ``today``.

    ``week_offset`` 0 is the current week, 1 is next week. Uses plain date arithmetic,
    so it handles the year boundary and 53-week ISO years correctly. ``today`` defaults to
    the current date in the site's ``TIME_ZONE``, not the server's OS clock.
    """
    today = today or timezone.localdate()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    return monday, monday + timedelta(days=6)
