"""Tests for the release-week issue lists (this week, next week, future)."""

from datetime import datetime, timedelta

from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertTemplateUsed

from comicsdb.models.issue import Issue
from comicsdb.models.series import Series

HTML_OK_CODE = 200
PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


# This week tests
def test_view_url_exists_at_desired_location(db, client):
    resp = client.get("/issue/thisweek")
    assert resp.status_code == HTML_OK_CODE


def test_view_url_accessible_by_name(db, client):
    resp = client.get(reverse("issue:thisweek"))
    assert resp.status_code == HTML_OK_CODE


def test_view_uses_correct_template(db, client):
    resp = client.get(reverse("issue:thisweek"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/week_list.html")


def test_pagination_is_thirty(db, client, list_of_issues):
    resp = client.get(reverse("issue:thisweek"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["issue_list"]) == PAGINATE_DEFAULT_VAL


def test_lists_second_page(db, client, list_of_issues):
    # Get second page and confirm it has (exactly) remaining 7 items
    resp = client.get(reverse("issue:thisweek") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["issue_list"]) == PAGINATE_DIFF_VAL


# Next week tests
def test_nextweek_view_url_exists_at_desired_location(db, client):
    resp = client.get("/issue/nextweek")
    assert resp.status_code == HTML_OK_CODE


def test_nextweek_view_url_accessible_by_name(db, client):
    resp = client.get(reverse("issue:nextweek"))
    assert resp.status_code == HTML_OK_CODE


def test_nextweek_view_uses_correct_template(db, client):
    resp = client.get(reverse("issue:nextweek"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/week_list.html")


# Future week tests
def test_future_view_url_exists_at_desired_location(db, client):
    resp = client.get("/issue/future")
    assert resp.status_code == HTML_OK_CODE


def test_future_view_url_accessible_by_name(db, client):
    resp = client.get(reverse("issue:future"))
    assert resp.status_code == HTML_OK_CODE


def test_future_view_uses_correct_template(db, client):
    resp = client.get(reverse("issue:future"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/week_list.html")


# TODO: Add test for issues with a store date greater than next weeks.


# Issue Week Views
def test_issue_week_view_anonymous_access(db, client):
    """Test that anonymous users can access week view."""
    resp = client.get(reverse("issue:thisweek"))
    assert resp.status_code == HTML_OK_CODE


def test_issue_next_week_view_anonymous_access(db, client):
    """Test that anonymous users can access next week view."""
    resp = client.get(reverse("issue:nextweek"))
    assert resp.status_code == HTML_OK_CODE


def test_issue_future_view_anonymous_access(db, client):
    """Test that anonymous users can access future view."""
    resp = client.get(reverse("issue:future"))
    assert resp.status_code == HTML_OK_CODE


def test_week_list_shows_current_week_issues(
    auto_login_user, create_user, dc_comics, single_issue_type
):
    """Test that WeekList shows issues for the current week."""
    client, user = auto_login_user()

    # Get current week info
    today = timezone.localdate()

    # Create series
    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2024,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    # Create issue for current week
    current_week_issue = Issue.objects.create(
        series=series,
        number="1",
        cover_date=today,
        store_date=today,
        created_by=user,
        edited_by=user,
    )

    # Create issue for next week
    next_week_date = today + timedelta(days=7)
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=next_week_date,
        store_date=next_week_date,
        created_by=user,
        edited_by=user,
    )

    # Test that WeekList shows only current week issue
    resp = client.get(reverse("issue:thisweek"))
    assert resp.status_code == HTML_OK_CODE
    assert current_week_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_next_week_list_shows_next_week_issues(
    auto_login_user, create_user, dc_comics, single_issue_type
):
    """Test that NextWeekList shows issues for next week."""
    client, user = auto_login_user()

    # Get current and next week info
    today = timezone.localdate()
    year, week, _ = today.isocalendar()

    # Calculate next week
    if week != 52:
        next_week = week + 1
        next_year = year
    else:
        next_week = 1
        next_year = year + 1

    # Create series
    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2024,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    # Create issue for current week
    Issue.objects.create(
        series=series,
        number="1",
        cover_date=today,
        store_date=today,
        created_by=user,
        edited_by=user,
    )

    # Use strptime to create a date that's guaranteed to be in the next week
    # The '1' in the format string gives the date for Monday of that week
    next_week_date = datetime.strptime(f"{next_year}-{next_week}-1", "%G-%V-%u").date()

    next_week_issue = Issue.objects.create(
        series=series,
        number="2",
        cover_date=next_week_date,
        store_date=next_week_date,
        created_by=user,
        edited_by=user,
    )

    # Create issue for two weeks ahead (week after next)
    if next_week != 52:
        two_weeks_week = next_week + 1
        two_weeks_year = next_year
    else:
        two_weeks_week = 1
        two_weeks_year = next_year + 1

    two_weeks_date = datetime.strptime(f"{two_weeks_year}-{two_weeks_week}-1", "%G-%V-%u").date()
    Issue.objects.create(
        series=series,
        number="3",
        cover_date=two_weeks_date,
        store_date=two_weeks_date,
        created_by=user,
        edited_by=user,
    )

    # Test that NextWeekList shows only next week issue
    resp = client.get(reverse("issue:nextweek"))
    assert resp.status_code == HTML_OK_CODE
    assert next_week_issue in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 1


def test_future_list_shows_future_issues(
    auto_login_user, create_user, dc_comics, single_issue_type
):
    """Test that FutureList shows issues beyond next week."""
    client, user = auto_login_user()

    today = timezone.localdate()

    # Create series
    series = Series.objects.create(
        name="Batman",
        publisher=dc_comics,
        series_type=single_issue_type,
        year_began=2024,
        status=Series.Status.ONGOING,
        volume=1,
        created_by=user,
        edited_by=user,
    )

    # Create issue for current week (should not appear in FutureList)
    Issue.objects.create(
        series=series,
        number="1",
        cover_date=today,
        store_date=today,
        created_by=user,
        edited_by=user,
    )

    # Create issue for next week (should not appear in FutureList)
    next_week_date = today + timedelta(days=7)
    Issue.objects.create(
        series=series,
        number="2",
        cover_date=next_week_date,
        store_date=next_week_date,
        created_by=user,
        edited_by=user,
    )

    # Create issue for two weeks ahead (should appear in FutureList)
    two_weeks_date = today + timedelta(days=14)
    future_issue_1 = Issue.objects.create(
        series=series,
        number="3",
        cover_date=two_weeks_date,
        store_date=two_weeks_date,
        created_by=user,
        edited_by=user,
    )

    # Create issue for four weeks ahead (should appear in FutureList)
    four_weeks_date = today + timedelta(days=28)
    future_issue_2 = Issue.objects.create(
        series=series,
        number="4",
        cover_date=four_weeks_date,
        store_date=four_weeks_date,
        created_by=user,
        edited_by=user,
    )

    # Test that FutureList shows only future issues (beyond next week)
    resp = client.get(reverse("issue:future"))
    assert resp.status_code == HTML_OK_CODE
    assert future_issue_1 in resp.context["issue_list"]
    assert future_issue_2 in resp.context["issue_list"]
    assert resp.context["issue_list"].count() == 2


def test_week_views_context_data(db, client):
    """Test that week views include required context data."""
    # Test WeekList
    resp = client.get(reverse("issue:thisweek"))
    assert resp.status_code == HTML_OK_CODE
    assert "release_day" in resp.context
    assert "future" in resp.context
    assert resp.context["future"] is False

    # Test NextWeekList
    resp = client.get(reverse("issue:nextweek"))
    assert resp.status_code == HTML_OK_CODE
    assert "release_day" in resp.context
    assert "future" in resp.context
    assert resp.context["future"] is False

    # Test FutureList
    resp = client.get(reverse("issue:future"))
    assert resp.status_code == HTML_OK_CODE
    assert "release_day" in resp.context
    assert "future" in resp.context
    assert resp.context["future"] is True
