from datetime import timedelta
from unittest.mock import Mock, patch

from django.urls import reverse
from django.utils import timezone
from django.utils.http import http_date, parse_http_date
from rest_framework import status

from comicsdb.cache import get_last_modified, set_last_modified
from comicsdb.models.arc import Arc
from comicsdb.models.issue import Issue


def _stale_since(resp):
    """Backdate a Last-Modified header by 2s, to dodge HTTP's 1s date resolution."""
    return http_date(parse_http_date(resp["Last-Modified"]) - 2)


def test_arc_returns_last_modified_header(api_client_with_credentials, wwh_arc):
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    assert "Last-Modified" in resp


def test_arc_conditional_request_returns_304(api_client_with_credentials, wwh_arc):
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_character_conditional_request_returns_304(api_client_with_credentials, superman):
    resp = api_client_with_credentials.get(
        reverse("api:character-detail", kwargs={"pk": superman.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:character-detail", kwargs={"pk": superman.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_creator_conditional_request_returns_304(api_client_with_credentials, john_byrne):
    resp = api_client_with_credentials.get(
        reverse("api:creator-detail", kwargs={"pk": john_byrne.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:creator-detail", kwargs={"pk": john_byrne.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_issue_conditional_request_returns_304(api_client_with_credentials, basic_issue):
    resp = api_client_with_credentials.get(
        reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:issue-detail", kwargs={"pk": basic_issue.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_publisher_conditional_request_returns_304(api_client_with_credentials, dc_comics):
    resp = api_client_with_credentials.get(
        reverse("api:publisher-detail", kwargs={"pk": dc_comics.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:publisher-detail", kwargs={"pk": dc_comics.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_series_conditional_request_returns_304(api_client_with_credentials, fc_series):
    resp = api_client_with_credentials.get(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_team_conditional_request_returns_304(api_client_with_credentials, teen_titans):
    resp = api_client_with_credentials.get(
        reverse("api:team-detail", kwargs={"pk": teen_titans.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:team-detail", kwargs={"pk": teen_titans.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_universe_conditional_request_returns_304(api_client_with_credentials, earth_2_universe):
    resp = api_client_with_credentials.get(
        reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_imprint_conditional_request_returns_304(api_client_with_credentials, vertigo_imprint):
    resp = api_client_with_credentials.get(
        reverse("api:imprint-detail", kwargs={"pk": vertigo_imprint.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:imprint-detail", kwargs={"pk": vertigo_imprint.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_conditional_request_with_old_date_returns_200(api_client_with_credentials, wwh_arc):
    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
        HTTP_IF_MODIFIED_SINCE="Wed, 01 Jan 2020 00:00:00 GMT",
    )
    assert resp.status_code == status.HTTP_200_OK


def test_list_endpoint_does_not_return_304(api_client_with_credentials, wwh_arc, fc_arc):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "Last-Modified" not in resp


def test_arc_issue_list_returns_last_modified_header(api_client_with_credentials, issue_with_arc):
    arc = issue_with_arc.arcs.first()
    resp = api_client_with_credentials.get(reverse("api:arc-issue-list", kwargs={"pk": arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    assert "Last-Modified" in resp


def test_arc_issue_list_conditional_request_returns_304(
    api_client_with_credentials, issue_with_arc
):
    arc = issue_with_arc.arcs.first()
    resp = api_client_with_credentials.get(reverse("api:arc-issue-list", kwargs={"pk": arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:arc-issue-list", kwargs={"pk": arc.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_character_issue_list_conditional_request_returns_304(
    api_client_with_credentials, superman
):
    resp = api_client_with_credentials.get(
        reverse("api:character-issue-list", kwargs={"pk": superman.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:character-issue-list", kwargs={"pk": superman.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_series_issue_list_conditional_request_returns_304(
    api_client_with_credentials, basic_issue
):
    resp = api_client_with_credentials.get(
        reverse("api:series-issue-list", kwargs={"pk": basic_issue.series.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:series-issue-list", kwargs={"pk": basic_issue.series.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_team_issue_list_conditional_request_returns_304(
    api_client_with_credentials, multi_story_issue, teen_titans
):
    resp = api_client_with_credentials.get(
        reverse("api:team-issue-list", kwargs={"pk": teen_titans.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:team-issue-list", kwargs={"pk": teen_titans.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_issue_list_conditional_request_with_old_date_returns_200(
    api_client_with_credentials, issue_with_arc
):
    arc = issue_with_arc.arcs.first()
    resp = api_client_with_credentials.get(
        reverse("api:arc-issue-list", kwargs={"pk": arc.pk}),
        HTTP_IF_MODIFIED_SINCE="Wed, 01 Jan 2020 00:00:00 GMT",
    )
    assert resp.status_code == status.HTTP_200_OK


def test_arc_detail_hit_avoids_db_fetch(api_client_with_credentials, wwh_arc):
    """A cache hit must short-circuit to 304 without calling get_object()."""
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    with patch(
        "api.views.CachedObjectMixin.get_object",
        side_effect=AssertionError("get_object() was called; cache was not consulted"),
    ):
        resp = api_client_with_credentials.get(
            reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
            HTTP_IF_MODIFIED_SINCE=last_modified,
        )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_arc_detail_hit_does_not_rewrite_cache(api_client_with_credentials, wwh_arc):
    """A cache hit must not re-write the unchanged value on every request."""
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    with patch("comicsdb.cache.cache.set") as mock_set:
        resp = api_client_with_credentials.get(
            reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
            HTTP_IF_MODIFIED_SINCE=last_modified,
        )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED
    mock_set.assert_not_called()


def test_arc_plain_get_does_not_touch_cache(api_client_with_credentials, wwh_arc):
    """A plain (non-conditional) GET - the majority of real traffic - always
    fetches from the DB anyway, so it should skip the cache entirely rather than
    read a value it won't use or write one back that's already correct."""
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK

    with patch("comicsdb.cache.cache") as mock_cache:
        resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    mock_cache.get.assert_not_called()
    mock_cache.set.assert_not_called()


def test_arc_conditional_request_self_heals_after_cache_flush(
    api_client_with_credentials, wwh_arc, isolated_last_modified_cache
):
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    isolated_last_modified_cache.clear()
    assert get_last_modified(Arc, wwh_arc.pk) is None

    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED
    assert get_last_modified(Arc, wwh_arc.pk) is not None


def test_arc_conditional_request_degrades_gracefully_when_cache_read_fails(
    api_client_with_credentials, wwh_arc
):
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    with patch("comicsdb.cache.cache.get", side_effect=Exception("redis down")):
        resp = api_client_with_credentials.get(
            reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
            HTTP_IF_MODIFIED_SINCE=last_modified,
        )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_arc_conditional_request_returns_200_after_save(api_client_with_credentials, wwh_arc):
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = _stale_since(resp)

    wwh_arc.desc = "updated description"
    wwh_arc.save()

    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_200_OK


def test_arc_conditional_request_200_uses_db_value_not_stale_cache(
    api_client_with_credentials, wwh_arc
):
    """When the cache indicates a change (so the response will be a 200 either
    way), the Last-Modified header must come from the DB fetch, not whatever
    value happened to be cached."""
    stale_cached = Mock(spec=["pk", "modified"])
    stale_cached.__class__ = Arc
    stale_cached.pk = wwh_arc.pk
    stale_cached.modified = wwh_arc.modified - timedelta(seconds=50)
    set_last_modified(stale_cached)

    since = http_date(int(wwh_arc.modified.timestamp()) - 100)

    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
        HTTP_IF_MODIFIED_SINCE=since,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert parse_http_date(resp["Last-Modified"]) == int(wwh_arc.modified.timestamp())


def test_arc_detail_returns_404_after_delete_not_304(
    api_client_with_credentials, wwh_arc, django_capture_on_commit_callbacks
):
    resp = api_client_with_credentials.get(reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]
    arc_pk = wwh_arc.pk

    # Cache invalidation runs on transaction.on_commit(); pytest-django's db
    # fixture wraps the test in a transaction that's rolled back rather than
    # committed, so the callback must be captured and executed explicitly to
    # simulate what happens on a real (committing) delete.
    with django_capture_on_commit_callbacks(execute=True):
        wwh_arc.delete()

    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": arc_pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_series_detail_conditional_request_returns_200_after_issue_added(
    api_client_with_credentials, fc_series, basic_issue
):
    resp = api_client_with_credentials.get(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = _stale_since(resp)

    Issue.objects.create(
        series=fc_series,
        number="2",
        slug="final-crisis-2",
        cover_date=timezone.now().date(),
        edited_by=basic_issue.edited_by,
        created_by=basic_issue.created_by,
    )

    resp = api_client_with_credentials.get(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_200_OK


def test_series_issue_list_conditional_request_returns_200_after_issue_added(
    api_client_with_credentials, fc_series, basic_issue
):
    resp = api_client_with_credentials.get(
        reverse("api:series-issue-list", kwargs={"pk": fc_series.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = _stale_since(resp)

    Issue.objects.create(
        series=fc_series,
        number="2",
        slug="final-crisis-2",
        cover_date=timezone.now().date(),
        edited_by=basic_issue.edited_by,
        created_by=basic_issue.created_by,
    )

    resp = api_client_with_credentials.get(
        reverse("api:series-issue-list", kwargs={"pk": fc_series.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_200_OK


def test_arc_issue_list_conditional_request_returns_200_after_issue_arc_added(
    api_client_with_credentials, wwh_arc, basic_issue
):
    resp = api_client_with_credentials.get(reverse("api:arc-issue-list", kwargs={"pk": wwh_arc.pk}))
    assert resp.status_code == status.HTTP_200_OK
    last_modified = _stale_since(resp)

    basic_issue.arcs.add(wwh_arc)

    resp = api_client_with_credentials.get(
        reverse("api:arc-issue-list", kwargs={"pk": wwh_arc.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_200_OK
