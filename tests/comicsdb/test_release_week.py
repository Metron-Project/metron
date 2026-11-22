"""Tests for release-week date ranges and the admin "future store week" filter."""

from datetime import UTC, date, datetime

import pytest
from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.utils import timezone

from comicsdb.admin.issue import FutureStoreDateListFilter
from comicsdb.models.issue import Issue
from comicsdb.release_week import release_week_bounds


@pytest.mark.parametrize(
    ("today", "week_offset", "expected"),
    [
        # Mid-week, mid-year.
        (date(2026, 6, 17), 0, (date(2026, 6, 15), date(2026, 6, 21))),
        (date(2026, 6, 17), 1, (date(2026, 6, 22), date(2026, 6, 28))),
        # Monday and Sunday are the first and last days of their own week.
        (date(2026, 6, 15), 0, (date(2026, 6, 15), date(2026, 6, 21))),
        (date(2026, 6, 21), 0, (date(2026, 6, 15), date(2026, 6, 21))),
        # Next week crosses into January (Dec 2025 is ISO week 52 of 52).
        (date(2025, 12, 24), 1, (date(2025, 12, 29), date(2026, 1, 4))),
        # 2026 has 53 ISO weeks: week 52 is followed by week 53, not week 1.
        (date(2026, 12, 23), 1, (date(2026, 12, 28), date(2027, 1, 3))),
        # Dec 30, 2024 is in ISO week 1 of 2025.
        (date(2024, 12, 30), 0, (date(2024, 12, 30), date(2025, 1, 5))),
    ],
)
def test_release_week_bounds(today, week_offset, expected):
    assert release_week_bounds(week_offset, today=today) == expected


def test_release_week_bounds_defaults_to_today():
    monday, sunday = release_week_bounds()
    assert monday <= timezone.localdate() <= sunday
    assert monday.weekday() == 0
    assert (sunday - monday).days == 6


@pytest.mark.parametrize(
    ("now_utc", "expected"),
    [
        # Mon Jun 22 02:00 UTC is still Sun Jun 21 in New York: stay on the Jun 15-21 week.
        (datetime(2026, 6, 22, 2, 0, tzinfo=UTC), (date(2026, 6, 15), date(2026, 6, 21))),
        # Mon Jun 22 05:00 UTC is Mon Jun 22 01:00 in New York: the new week has started.
        (datetime(2026, 6, 22, 5, 0, tzinfo=UTC), (date(2026, 6, 22), date(2026, 6, 28))),
    ],
)
def test_release_week_bounds_uses_site_timezone(settings, monkeypatch, now_utc, expected):
    """The default ``today`` follows ``TIME_ZONE``, not the UTC (or OS) date."""
    settings.TIME_ZONE = "America/New_York"
    monkeypatch.setattr(timezone, "now", lambda: now_utc)
    assert release_week_bounds() == expected


@pytest.fixture
def frozen_today(monkeypatch):
    """Make ``release_week`` see a fixed ``timezone.localdate()``."""

    def freeze(day):
        monkeypatch.setattr(timezone, "localdate", lambda: day)

    return freeze


def _filter_issues(value):
    request = RequestFactory().get("/")
    list_filter = FutureStoreDateListFilter(
        request, {"store_date": [value]}, Issue, site._registry[Issue]
    )
    return list_filter.queryset(request, Issue.objects.all())


@pytest.mark.parametrize(
    ("value", "included", "excluded"),
    [
        # Today is Wed Dec 23, 2026; this week is Dec 21-27 and next week Dec 28-Jan 3.
        ("thisWeek", [date(2026, 12, 21), date(2026, 12, 27)], [date(2026, 12, 28)]),
        (
            "nextWeek",
            [date(2026, 12, 28), date(2027, 1, 3)],
            [date(2026, 12, 27), date(2027, 1, 4)],
        ),
    ],
)
def test_future_store_week_filter_across_year_end(
    frozen_today, basic_issue, value, included, excluded
):
    frozen_today(date(2026, 12, 23))
    issues = {}
    for i, store_date in enumerate([*included, *excluded]):
        issues[store_date] = Issue.objects.create(
            series=basic_issue.series,
            number=f"{100 + i}",
            slug=f"week-filter-{i}",
            cover_date=store_date,
            store_date=store_date,
            edited_by=basic_issue.edited_by,
            created_by=basic_issue.created_by,
        )

    result = set(_filter_issues(value))

    assert {issues[d] for d in included} <= result
    assert not {issues[d] for d in excluded} & result


def test_future_store_week_filter_no_value_returns_none(db):
    request = RequestFactory().get("/")
    list_filter = FutureStoreDateListFilter(request, {}, Issue, site._registry[Issue])
    assert list_filter.queryset(request, Issue.objects.all()) is None
