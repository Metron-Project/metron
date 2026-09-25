"""Tests for the pull list detail view: filtering, view modes, FOC flags, and undo."""

from datetime import timedelta

import pytest
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format

from pull_list.models import PullListSeries
from pull_list.views import FOC_WARNING_DAYS, UNDO_SESSION_KEY

DETAIL_URL = reverse("pull-list:detail")


@pytest.fixture
def logged_in_client(client, pull_list_user, test_password):
    client.login(username=pull_list_user.username, password=test_password)
    return client


@pytest.fixture
def pull_list_with_two_series(pull_list_with_series, pull_list_series_2):
    PullListSeries.objects.create(pull_list=pull_list_with_series, series=pull_list_series_2)
    return pull_list_with_series


# Upcoming issues
def test_upcoming_excludes_past_issues(
    logged_in_client, pull_list_with_series, pull_list_series, make_pull_list_issue
):
    past = make_pull_list_issue(pull_list_series, 1, store_in_days=-1)
    today = make_pull_list_issue(pull_list_series, 2, store_in_days=0)
    resp = logged_in_client.get(DETAIL_URL)
    upcoming = resp.context["upcoming_issues"]
    assert today in upcoming
    assert past not in upcoming


def test_upcoming_excludes_series_not_on_list(
    logged_in_client,
    pull_list_with_series,
    pull_list_series,
    pull_list_series_2,
    make_pull_list_issue,
):
    on_list = make_pull_list_issue(pull_list_series, 1, store_in_days=3)
    not_on_list = make_pull_list_issue(pull_list_series_2, 1, store_in_days=3)
    resp = logged_in_client.get(DETAIL_URL)
    upcoming = resp.context["upcoming_issues"]
    assert on_list in upcoming
    assert not_on_list not in upcoming


def test_upcoming_ordered_by_store_date(
    logged_in_client, pull_list_with_series, pull_list_series, make_pull_list_issue
):
    later = make_pull_list_issue(pull_list_series, 2, store_in_days=14)
    sooner = make_pull_list_issue(pull_list_series, 1, store_in_days=7)
    resp = logged_in_client.get(DETAIL_URL)
    assert resp.context["upcoming_issues"] == [sooner, later]
    assert resp.context["next_release"] == sooner.store_date


def test_next_release_none_without_upcoming(logged_in_client, pull_list_with_series):
    resp = logged_in_client.get(DETAIL_URL)
    assert resp.context["upcoming_issues"] == []
    assert resp.context["next_release"] is None


def test_series_next_store_date(
    logged_in_client,
    pull_list_with_two_series,
    pull_list_series,
    pull_list_series_2,
    make_pull_list_issue,
):
    make_pull_list_issue(pull_list_series, 1, store_in_days=-7)
    nearest = make_pull_list_issue(pull_list_series, 2, store_in_days=5)
    make_pull_list_issue(pull_list_series, 3, store_in_days=12)
    resp = logged_in_client.get(DETAIL_URL)
    next_dates = {pls.series_id: pls.next_store_date for pls in resp.context["series_on_list"]}
    assert next_dates[pull_list_series.pk] == nearest.store_date
    assert next_dates[pull_list_series_2.pk] is None


# Series filter
def test_series_filter_limits_upcoming(
    logged_in_client,
    pull_list_with_two_series,
    pull_list_series,
    pull_list_series_2,
    make_pull_list_issue,
):
    wanted = make_pull_list_issue(pull_list_series, 1, store_in_days=3)
    make_pull_list_issue(pull_list_series_2, 1, store_in_days=3)
    resp = logged_in_client.get(DETAIL_URL, {"series": pull_list_series.pk})
    assert resp.context["active_series"] == pull_list_series
    assert resp.context["upcoming_issues"] == [wanted]


@pytest.mark.parametrize("value", ["abc", "", "-1", "999999"])
def test_series_filter_ignores_invalid_values(logged_in_client, pull_list_with_series, value):
    resp = logged_in_client.get(DETAIL_URL, {"series": value})
    assert resp.status_code == 200
    assert resp.context["active_series"] is None


def test_series_filter_ignores_series_not_on_list(
    logged_in_client, pull_list_with_series, pull_list_series_2
):
    resp = logged_in_client.get(DETAIL_URL, {"series": pull_list_series_2.pk})
    assert resp.context["active_series"] is None


def test_filter_shows_clear_filter_link(logged_in_client, pull_list_with_series, pull_list_series):
    resp = logged_in_client.get(DETAIL_URL, {"series": pull_list_series.pk, "view": "covers"})
    content = resp.content.decode()
    assert "Clear filter" in content
    assert "Select to filter" not in content
    # The active series links back to the unfiltered list, keeping the view mode.
    assert 'aria-current="true"' in content
    assert 'hx-get="?view=covers"' in content


def test_no_filter_shows_select_hint(logged_in_client, pull_list_with_series):
    content = logged_in_client.get(DETAIL_URL).content.decode()
    assert "Select to filter" in content
    assert "Clear filter" not in content
    assert 'aria-current="true"' not in content


# View mode
@pytest.mark.parametrize(
    ("param", "expected"),
    [(None, "list"), ("list", "list"), ("covers", "covers"), ("bogus", "list")],
)
def test_view_mode(logged_in_client, pull_list_with_series, param, expected):
    data = {"view": param} if param else {}
    resp = logged_in_client.get(DETAIL_URL, data)
    assert resp.context["view_mode"] == expected


def test_view_toggle_keeps_series_filter(logged_in_client, pull_list_with_series, pull_list_series):
    resp = logged_in_client.get(DETAIL_URL, {"series": pull_list_series.pk})
    content = resp.content.decode()
    assert f'hx-get="?view=covers&series={pull_list_series.pk}"' in content


# Final order cutoff flags
@pytest.mark.parametrize(
    ("foc_in_days", "foc_soon", "foc_later"),
    [
        (0, True, False),
        (FOC_WARNING_DAYS, True, False),
        (FOC_WARNING_DAYS + 1, False, True),
        (-1, False, False),
        (None, False, False),
    ],
)
def test_foc_flags(
    logged_in_client,
    pull_list_with_series,
    pull_list_series,
    make_pull_list_issue,
    foc_in_days,
    foc_soon,
    foc_later,
):
    make_pull_list_issue(pull_list_series, 1, store_in_days=21, foc_in_days=foc_in_days)
    resp = logged_in_client.get(DETAIL_URL)
    (issue,) = resp.context["upcoming_issues"]
    assert issue.foc_soon is foc_soon
    assert issue.foc_later is foc_later
    assert (issue in resp.context["foc_soon_issues"]) is foc_soon


def test_foc_soon_shows_notification(
    logged_in_client, pull_list_with_series, pull_list_series, make_pull_list_issue
):
    make_pull_list_issue(pull_list_series, 1, store_in_days=21, foc_in_days=2)
    content = logged_in_client.get(DETAIL_URL).content.decode()
    assert "Final order cutoff" in content
    assert "tag is-warning" in content


def test_foc_later_shows_info_tag(
    logged_in_client, pull_list_with_series, pull_list_series, make_pull_list_issue
):
    make_pull_list_issue(pull_list_series, 1, store_in_days=21, foc_in_days=14)
    content = logged_in_client.get(DETAIL_URL).content.decode()
    assert "Final order cutoff" not in content
    assert "tag is-info" in content


# Empty state
def test_empty_pull_list_shows_empty_state(logged_in_client, pull_list):
    content = logged_in_client.get(DETAIL_URL).content.decode()
    assert "Your pull list is empty" in content
    assert "Upcoming issues" not in content


# Remove + undo
def test_remove_stores_undo_in_session(logged_in_client, pull_list_with_series, pull_list_series):
    logged_in_client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk})
    )
    assert logged_in_client.session[UNDO_SESSION_KEY] == {
        "pk": pull_list_series.pk,
        "name": str(pull_list_series),
    }


def test_htmx_remove_renders_undo_once(logged_in_client, pull_list_with_series, pull_list_series):
    resp = logged_in_client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk}),
        headers={"HX-Request": "true"},
        follow=True,
    )
    content = resp.content.decode()
    removed_msg = f"Removed {pull_list_series} from your pull list."
    # The notification is inside #pull-list-content, so HTMX swaps it in.
    assert removed_msg in content.split('id="pull-list-content"', 1)[1]
    assert f'name="series" value="{pull_list_series.pk}"' in content
    assert UNDO_SESSION_KEY not in logged_in_client.session

    # The undo offer is consumed after one render.
    content = logged_in_client.get(DETAIL_URL).content.decode()
    assert removed_msg not in content


def test_undo_restores_series(logged_in_client, pull_list_with_series, pull_list_series):
    logged_in_client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk})
    )
    logged_in_client.post(DETAIL_URL, {"series": pull_list_series.pk})
    assert PullListSeries.objects.filter(
        pull_list=pull_list_with_series, series=pull_list_series
    ).exists()


def test_htmx_undo_does_not_queue_message(
    logged_in_client, pull_list_with_series, pull_list_series
):
    logged_in_client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk})
    )
    resp = logged_in_client.post(
        DETAIL_URL, {"series": pull_list_series.pk}, headers={"HX-Request": "true"}
    )
    assert resp.status_code == 302
    assert not list(get_messages(resp.wsgi_request))


def test_remove_keeps_filter_and_view(
    logged_in_client, pull_list_with_two_series, pull_list_series, pull_list_series_2
):
    resp = logged_in_client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series_2.pk}),
        QUERY_STRING=f"view=covers&series={pull_list_series.pk}",
    )
    assert resp.url == f"{DETAIL_URL}?view=covers&series={pull_list_series.pk}"


def test_remove_active_series_drops_filter(
    logged_in_client, pull_list_with_series, pull_list_series
):
    resp = logged_in_client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk}),
        QUERY_STRING=f"view=covers&series={pull_list_series.pk}",
    )
    assert resp.url == f"{DETAIL_URL}?view=covers"


def test_undo_keeps_filter_and_view(logged_in_client, pull_list, pull_list_series):
    resp = logged_in_client.post(
        DETAIL_URL,
        {"series": pull_list_series.pk},
        QUERY_STRING=f"view=covers&series={pull_list_series.pk}",
    )
    assert resp.url == f"{DETAIL_URL}?view=covers&series={pull_list_series.pk}"


def test_forms_carry_filter_query(logged_in_client, pull_list_with_series, pull_list_series):
    resp = logged_in_client.get(DETAIL_URL, {"series": pull_list_series.pk, "view": "covers"})
    remove_url = reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk})
    assert f"{remove_url}?view=covers&amp;series={pull_list_series.pk}" in resp.content.decode()


def test_remove_other_users_series_is_404(
    client, other_pull_list_user, test_password, pull_list_with_series, pull_list_series
):
    client.login(username=other_pull_list_user.username, password=test_password)
    resp = client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk})
    )
    assert resp.status_code == 404
    assert PullListSeries.objects.filter(pull_list=pull_list_with_series).exists()


# Release day countdown
@pytest.mark.parametrize(("store_in_days", "expected"), [(0, "Today"), (1, "In 1\xa0day")])
def test_release_day_countdown(
    logged_in_client,
    pull_list_with_series,
    pull_list_series,
    make_pull_list_issue,
    store_in_days,
    expected,
):
    make_pull_list_issue(pull_list_series, 1, store_in_days=store_in_days)
    content = logged_in_client.get(DETAIL_URL).content.decode()
    assert expected in content
    assert "minutes" not in content
    assert "hours" not in content


# FOC banner and header summary
def test_foc_banner_shows_each_cutoff_date(
    logged_in_client, pull_list_with_series, pull_list_series, make_pull_list_issue
):
    # Ships first but has the later cutoff.
    make_pull_list_issue(pull_list_series, 1, store_in_days=10, foc_in_days=6)
    make_pull_list_issue(pull_list_series, 2, store_in_days=20, foc_in_days=2)
    resp = logged_in_client.get(DETAIL_URL)
    assert [i.number for i in resp.context["foc_soon_issues"]] == ["2", "1"]
    content = resp.content.decode()
    today = timezone.localdate()
    for days in (2, 6):
        cutoff = date_format(today + timedelta(days=days), "l, M j")
        assert f"Final order cutoff {cutoff}" in content


def test_summary_and_foc_banner_ignore_filter(
    logged_in_client,
    pull_list_with_two_series,
    pull_list_series,
    pull_list_series_2,
    make_pull_list_issue,
):
    make_pull_list_issue(pull_list_series, 1, store_in_days=10)
    other = make_pull_list_issue(pull_list_series_2, 1, store_in_days=3, foc_in_days=1)
    resp = logged_in_client.get(DETAIL_URL, {"series": pull_list_series.pk})
    assert resp.context["upcoming_count"] == 2
    assert resp.context["shown_count"] == 1
    assert resp.context["next_release"] == other.store_date
    assert resp.context["foc_soon_issues"] == [other]


def test_counts_are_not_capped(
    monkeypatch, logged_in_client, pull_list_with_series, pull_list_series, make_pull_list_issue
):
    monkeypatch.setattr("pull_list.views.UPCOMING_LIMIT", 2)
    for n in range(3):
        make_pull_list_issue(pull_list_series, n + 1, store_in_days=n + 1)
    resp = logged_in_client.get(DETAIL_URL)
    assert len(resp.context["upcoming_issues"]) == 2
    assert resp.context["upcoming_count"] == 3
    assert resp.context["shown_count"] == 3
    assert "Showing the next 2 issues." in resp.content.decode()


# Query count
def test_detail_query_count(
    logged_in_client,
    pull_list_with_two_series,
    pull_list_series,
    pull_list_series_2,
    make_pull_list_issue,
    django_assert_num_queries,
):
    make_pull_list_issue(pull_list_series, 1, store_in_days=3, foc_in_days=2)
    make_pull_list_issue(pull_list_series_2, 1, store_in_days=5, foc_in_days=12)
    # session, request.user, pull list, series on list, next store dates, upcoming issues.
    # The pull list reuses request.user, and the unfiltered, uncapped page derives its
    # counts and FOC banner from the loaded issues instead of querying again.
    with django_assert_num_queries(6):
        logged_in_client.get(DETAIL_URL)
