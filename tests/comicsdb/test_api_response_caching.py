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


def test_user_scoped_viewsets_are_not_list_cached():
    """CollectionViewSet/PullListViewSet/WishListViewSet are user-scoped
    (get_queryset filters by request.user) -- they must never use
    CachedListModelMixin, since a shared list cache key would serve one
    user's private data to another. This is a cheap regression guard for
    that intentional exclusion; see api/views.py."""
    for viewset in (CollectionViewSet, PullListViewSet, WishListViewSet):
        assert getattr(viewset, "cache_model_label", None) is None
