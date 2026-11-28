from datetime import date, timedelta
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils import timezone

from comicsdb.maintenance import (
    CHECKS,
    LIMITED_STALE_DAYS,
    ONGOING_STALE_DAYS,
    UNRELEASED_GRACE_DAYS,
    UNRELEASED_WINDOW_DAYS,
    MaintenanceCheck,
    stale_limited_series,
    stale_ongoing_series,
    unreleased_issues,
)
from comicsdb.models import Credits, Issue, Series, SeriesType

TODAY = date(2026, 6, 15)


@pytest.fixture
def make_series(create_user, dc_comics):
    user = create_user()
    counter = iter(range(1000))

    def _make(series_type_id=SeriesType.LIMITED_SERIES, status=Series.Status.ONGOING):
        n = next(counter)
        return Series.objects.create(
            name=f"Test Series {n}",
            slug=f"test-series-{n}",
            sort_name=f"Test Series {n}",
            publisher=dc_comics,
            volume=1,
            year_began=2024,
            series_type_id=series_type_id,
            status=status,
            edited_by=user,
            created_by=user,
        )

    return _make


@pytest.fixture
def make_issue(create_user):
    user = create_user()
    counter = iter(range(1000))

    def _make(series, store_date=None, cover_date=None):
        n = next(counter)
        return Issue.objects.create(
            series=series,
            number=str(n),
            slug=f"{series.slug}-{n}",
            cover_date=cover_date or store_date or TODAY,
            store_date=store_date,
            edited_by=user,
            created_by=user,
        )

    return _make


def days_ago(days: int) -> date:
    return TODAY - timedelta(days=days)


# Stale Limited Series


def test_stale_limited_series_included(make_series, make_issue):
    series = make_series()
    make_issue(series, store_date=days_ago(LIMITED_STALE_DAYS + 200))
    make_issue(series, store_date=days_ago(LIMITED_STALE_DAYS + 1))
    result = list(stale_limited_series(TODAY))
    assert result == [series]
    assert result[0].issue_count == 2
    assert result[0].last_date == days_ago(LIMITED_STALE_DAYS + 1)


def test_stale_limited_series_recent_issue_excluded(make_series, make_issue):
    series = make_series()
    make_issue(series, store_date=days_ago(LIMITED_STALE_DAYS - 1))
    assert not stale_limited_series(TODAY).exists()


def test_stale_limited_series_future_issue_excluded(make_series, make_issue):
    series = make_series()
    make_issue(series, store_date=days_ago(LIMITED_STALE_DAYS + 200))
    make_issue(series, store_date=TODAY + timedelta(days=30))
    assert not stale_limited_series(TODAY).exists()


def test_stale_limited_series_falls_back_to_cover_date(make_series, make_issue):
    series = make_series()
    make_issue(series, cover_date=days_ago(LIMITED_STALE_DAYS + 30))
    assert list(stale_limited_series(TODAY)) == [series]


def test_stale_limited_series_completed_excluded(make_series, make_issue):
    series = make_series(status=Series.Status.COMPLETED)
    make_issue(series, store_date=days_ago(LIMITED_STALE_DAYS + 200))
    assert not stale_limited_series(TODAY).exists()


def test_stale_limited_series_other_type_excluded(make_series, make_issue):
    series = make_series(series_type_id=SeriesType.SINGLE_ISSUE)
    make_issue(series, store_date=days_ago(LIMITED_STALE_DAYS + 200))
    assert not stale_limited_series(TODAY).exists()


def test_stale_limited_series_no_issues_excluded(make_series):
    make_series()
    assert not stale_limited_series(TODAY).exists()


# Stale ongoing series


def test_stale_ongoing_series_threshold(make_series, make_issue):
    stale = make_series(series_type_id=SeriesType.SINGLE_ISSUE)
    make_issue(stale, store_date=days_ago(ONGOING_STALE_DAYS + 1))
    fresh = make_series(series_type_id=SeriesType.SINGLE_ISSUE)
    make_issue(fresh, store_date=days_ago(ONGOING_STALE_DAYS - 1))
    assert list(stale_ongoing_series(TODAY)) == [stale]


def test_stale_ongoing_series_hiatus_excluded(make_series, make_issue):
    series = make_series(series_type_id=SeriesType.SINGLE_ISSUE, status=Series.Status.HIATUS)
    make_issue(series, store_date=days_ago(ONGOING_STALE_DAYS + 100))
    assert not stale_ongoing_series(TODAY).exists()


# Unreleased issues


def test_unreleased_issue_included(make_series, make_issue):
    issue = make_issue(make_series(), store_date=days_ago(UNRELEASED_GRACE_DAYS + 1))
    assert list(unreleased_issues(TODAY)) == [issue]


def test_unreleased_issue_with_credits_excluded(make_series, make_issue, john_byrne, writer):
    issue = make_issue(make_series(), store_date=days_ago(UNRELEASED_GRACE_DAYS + 1))
    credit = Credits.objects.create(issue=issue, creator=john_byrne)
    credit.role.add(writer)
    assert not unreleased_issues(TODAY).exists()


def test_unreleased_issue_digital_chapters_excluded(make_series, make_issue):
    series = make_series(series_type_id=SeriesType.DIGITAL_CHAPTERS)
    make_issue(series, store_date=days_ago(UNRELEASED_GRACE_DAYS + 1))
    assert not unreleased_issues(TODAY).exists()


def test_unreleased_issue_within_grace_excluded(make_series, make_issue):
    make_issue(make_series(), store_date=days_ago(UNRELEASED_GRACE_DAYS - 1))
    assert not unreleased_issues(TODAY).exists()


def test_unreleased_issue_outside_window_excluded(make_series, make_issue):
    make_issue(make_series(), store_date=days_ago(UNRELEASED_WINDOW_DAYS + 1))
    assert not unreleased_issues(TODAY).exists()


def test_unreleased_issue_no_store_date_excluded(make_series, make_issue):
    make_issue(make_series(), cover_date=days_ago(UNRELEASED_GRACE_DAYS + 30))
    assert not unreleased_issues(TODAY).exists()


# Views


def test_overview_requires_login(client):
    resp = client.get(reverse("maintenance:overview"))
    assert resp.status_code == 302
    assert "login" in resp.url


def test_check_requires_login(client):
    resp = client.get(reverse("maintenance:check", args=["unreleased-issues"]))
    assert resp.status_code == 302


def test_unknown_check_requires_login(client):
    resp = client.get(reverse("maintenance:check", args=["does-not-exist"]))
    assert resp.status_code == 302
    assert "login" in resp.url


def test_overview_logged_in(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("maintenance:overview"))
    assert resp.status_code == 200
    assert len(resp.context["checks"]) == len(CHECKS)


@pytest.mark.parametrize("slug", list(CHECKS))
def test_check_list_logged_in(auto_login_user, make_series, make_issue, slug):
    series_type = (
        SeriesType.SINGLE_ISSUE if slug == "stale-ongoing-series" else SeriesType.LIMITED_SERIES
    )
    series = make_series(series_type_id=series_type)
    make_issue(series, store_date=timezone.localdate() - timedelta(days=ONGOING_STALE_DAYS + 1))
    if slug == "unreleased-issues":
        make_issue(
            series, store_date=timezone.localdate() - timedelta(days=UNRELEASED_GRACE_DAYS + 1)
        )
    client, _ = auto_login_user()
    resp = client.get(reverse("maintenance:check", args=[slug]))
    assert resp.status_code == 200
    assert resp.context["maintenance_check"] is CHECKS[slug]
    assert len(resp.context["items"]) >= 1


def test_unknown_check_404(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("maintenance:check", args=["does-not-exist"]))
    assert resp.status_code == 404


def test_overview_counts_match_check_pages(auto_login_user, make_series, make_issue):
    series = make_series()
    make_issue(series, store_date=timezone.localdate() - timedelta(days=LIMITED_STALE_DAYS + 1))
    client, _ = auto_login_user()
    overview = client.get(reverse("maintenance:overview"))
    for check, count in overview.context["checks"]:
        resp = client.get(reverse("maintenance:check", args=[check.slug]))
        expected = resp.context["paginator"].count if resp.context["items"] else 0
        assert count == expected
    counts = {check.slug: count for check, count in overview.context["checks"]}
    assert counts["stale-limited-series"] == 1


def test_overview_count_uses_intcomma(auto_login_user):
    queryset = MagicMock()
    queryset.count.return_value = 12345
    fake = MaintenanceCheck(
        slug="fake-check",
        title="Fake",
        description="Fake",
        suggested_fix="Fake",
        kind="issue",
        queryset=lambda _today: queryset,
    )
    client, _ = auto_login_user()
    with patch("comicsdb.views.maintenance.CHECKS", {fake.slug: fake}):
        resp = client.get(reverse("maintenance:overview"))
    assert "12,345 items" in resp.content.decode()


def test_check_page_count_uses_intcomma(auto_login_user, make_series, make_issue):
    make_issue(
        make_series(),
        store_date=timezone.localdate() - timedelta(days=UNRELEASED_GRACE_DAYS + 1),
    )
    client, _ = auto_login_user()
    with patch.object(Paginator, "count", new_callable=PropertyMock, return_value=12345):
        resp = client.get(reverse("maintenance:check", args=["unreleased-issues"]))
    assert "<strong>12,345</strong> items" in resp.content.decode()
