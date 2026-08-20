import uuid
from unittest.mock import patch

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from api.views import CollectionViewSet, PullListViewSet, WishListViewSet
from comicsdb.models import Credits


@pytest.fixture
def local_cache():
    """Isolate the response cache so assertions about exact hit/miss/version
    behavior aren't affected by concurrent xdist workers sharing the real
    Redis backend (the `cachever:*` counters are global-per-model)."""
    test_cache = LocMemCache(f"test-api-response-caching-{uuid.uuid4()}", {})
    with patch("api.views.cache", test_cache), patch("api.cache.cache", test_cache):
        yield test_cache


def test_issue_retrieve_cache_hit_skips_heavy_query(
    api_client_with_credentials, basic_issue, local_cache
):
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    first_body = resp.json()

    with CaptureQueriesContext(connection) as queries:
        resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json() == first_body

    # Cache hit: none of the heavy prefetch/join queries the full retrieve
    # queryset would run should appear -- only the cheap (pk, modified)
    # lookup used for the conditional-request/cache-key check.
    sql_statements = [q["sql"] for q in queries.captured_queries]
    assert not any("comicsdb_credits" in sql for sql in sql_statements)
    assert not any("comicsdb_issue_arcs" in sql for sql in sql_statements)


def test_issue_retrieve_after_update_is_not_stale(
    api_client_with_staff_credentials, basic_issue, local_cache
):
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["desc"] != "Updated description"

    resp = api_client_with_staff_credentials.patch(url, {"desc": "Updated description"})
    assert resp.status_code == status.HTTP_200_OK

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["desc"] == "Updated description"


def test_credits_change_busts_issue_detail_cache(
    api_client_with_staff_credentials, basic_issue, john_byrne, writer, local_cache
):
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["credits"] == []

    credit = Credits.objects.create(issue=basic_issue, creator=john_byrne)
    credit.role.add(writer)

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["credits"]) == 1
    assert resp.json()["credits"][0]["creator"] == john_byrne.name


def test_arc_list_reflects_newly_created_arc(
    api_client_with_staff_credentials, wwh_arc, local_cache
):
    url = reverse("api:arc-list")
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["count"] == 1

    resp = api_client_with_staff_credentials.post(url, {"name": "Final Crisis", "desc": "New arc"})
    assert resp.status_code == status.HTTP_201_CREATED

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["count"] == 2


def test_arc_list_reflects_deleted_arc_via_admin(
    api_client_with_credentials, wwh_arc, fc_arc, local_cache
):
    url = reverse("api:arc-list")
    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["count"] == 2

    fc_arc.delete()

    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["count"] == 1


def test_series_list_reflects_new_issue_num_issues(
    api_client_with_staff_credentials, fc_series, basic_issue, local_cache
):
    url = reverse("api:series-list")
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    result = next(r for r in resp.json()["results"] if r["id"] == fc_series.pk)
    assert result["issue_count"] == 1

    resp = api_client_with_staff_credentials.post(
        reverse("api:issue-list"),
        {"series": fc_series.pk, "number": "2", "cover_date": "2008-01-01"},
    )
    assert resp.status_code == status.HTTP_201_CREATED

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    result = next(r for r in resp.json()["results"] if r["id"] == fc_series.pk)
    assert result["issue_count"] == 2


def test_publisher_series_list_reflects_new_series(
    api_client_with_staff_credentials, dc_comics, fc_series, single_issue_type, local_cache
):
    url = reverse("api:publisher-series-list", kwargs={"pk": dc_comics.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["count"] == 1

    resp = api_client_with_staff_credentials.post(
        reverse("api:series-list"),
        {
            "name": "New Series",
            "sort_name": "New Series",
            "volume": 1,
            "publisher": dc_comics.pk,
            "series_type": single_issue_type.pk,
            "year_began": 2024,
            "status": 4,
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["count"] == 2


def test_publisher_series_list_404s_after_publisher_deleted(
    api_client_with_staff_credentials, dc_comics, fc_series, local_cache
):
    """series_list must call get_object() (existence check) before serving
    a cache hit -- otherwise a deleted publisher's cached series list would
    keep returning 200 instead of 404 until the list cache TTL expires."""
    url = reverse("api:publisher-series-list", kwargs={"pk": dc_comics.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK

    fc_series.delete()
    dc_comics.delete()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_arc_issue_list_reflects_issue_field_edit(
    api_client_with_staff_credentials, issue_with_arc, fc_arc, local_cache
):
    """issue_list is cached under the parent Arc's own `modified`, which
    only bumps on M2M add/remove/clear -- not on a plain field edit to one
    of the linked issues. cache_action_dependent_labels ties the cache key
    to the Issue model's version counter too, so an edit like this should
    still be visible without waiting for the parent's `modified` to catch
    up."""
    url = reverse("api:arc-issue-list", kwargs={"pk": fc_arc.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"][0]["number"] == "1"

    issue_with_arc.number = "2"
    issue_with_arc.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"][0]["number"] == "2"


def test_series_retrieve_after_publisher_rename_is_not_stale(
    api_client_with_staff_credentials, fc_series, dc_comics, local_cache
):
    """Series retrieve embeds the Publisher's name, but renaming a
    Publisher doesn't bump the owning Series' `modified`.
    cache_detail_dependent_labels ties the Series detail cache key to the
    Publisher model's version counter too, so the rename should show up
    without waiting on the Series' own `modified`."""
    url = reverse("api:series-detail", kwargs={"pk": fc_series.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["publisher"]["name"] == "DC Comics"

    dc_comics.name = "DC Comics Renamed"
    dc_comics.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["publisher"]["name"] == "DC Comics Renamed"


def test_credit_role_add_after_create_does_not_stick_empty_roles(
    api_client_with_staff_credentials, basic_issue, john_byrne, writer, local_cache
):
    """CreditSerializer.create() calls Credits.objects.create() (bumping
    Issue.modified once) and only then credit.role.add(...). A request
    landing between those two steps -- simulated here by fetching before
    role.add() runs -- must not permanently cache the issue with an empty
    role list: the m2m_changed bump on role.add() has to produce a new
    `modified` value so the stale entry is orphaned rather than reused."""
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})

    credit = Credits.objects.create(issue=basic_issue, creator=john_byrne)

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["credits"][0]["role"] == []

    credit.role.add(writer)

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["credits"][0]["role"][0]["name"] == "Writer"


def test_issue_retrieve_after_series_rename_is_not_stale(
    api_client_with_staff_credentials, basic_issue, fc_series, local_cache
):
    """Issue retrieve embeds its Series' name, but renaming a Series
    doesn't bump the owning Issue's `modified`. cache_detail_dependent_labels
    ties the Issue detail cache key to the Series model's version counter
    too, so the rename should show up without waiting on the Issue's own
    `modified`."""
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["series"]["name"] == "Final Crisis"

    fc_series.name = "Final Crisis Renamed"
    fc_series.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["series"]["name"] == "Final Crisis Renamed"


def test_imprint_retrieve_after_publisher_rename_is_not_stale(
    api_client_with_staff_credentials, vertigo_imprint, dc_comics, local_cache
):
    """Imprint retrieve embeds its Publisher's name, but renaming a
    Publisher doesn't bump the owning Imprint's `modified`."""
    url = reverse("api:imprint-detail", kwargs={"pk": vertigo_imprint.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["publisher"]["name"] == "DC Comics"

    dc_comics.name = "DC Comics Renamed"
    dc_comics.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["publisher"]["name"] == "DC Comics Renamed"


def test_arc_issue_list_reflects_series_rename(
    api_client_with_staff_credentials, issue_with_arc, fc_arc, fc_series, local_cache
):
    """issue_list nests each issue's Series name; renaming the Series
    doesn't bump the parent Arc's `modified`."""
    url = reverse("api:arc-issue-list", kwargs={"pk": fc_arc.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"][0]["series"]["name"] == "Final Crisis"

    fc_series.name = "Final Crisis Renamed"
    fc_series.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"][0]["series"]["name"] == "Final Crisis Renamed"


def test_user_scoped_viewsets_are_not_list_cached():
    """CollectionViewSet/PullListViewSet/WishListViewSet are user-scoped
    (get_queryset filters by request.user) -- they must never use
    CachedListModelMixin, since a shared list cache key would serve one
    user's private data to another. This is a cheap regression guard for
    that intentional exclusion; see api/views.py."""
    for viewset in (CollectionViewSet, PullListViewSet, WishListViewSet):
        assert getattr(viewset, "cache_model_label", None) is None
