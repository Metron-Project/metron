import uuid
from unittest.mock import patch

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

from api.views import CollectionViewSet, PullListViewSet, WishListViewSet
from comicsdb.models import Credits, Issue, Variant


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


def test_arc_issue_list_after_issue_field_edit_is_accepted_staleness(
    api_client_with_staff_credentials, issue_with_arc, fc_arc, local_cache
):
    """issue_list is cached under the parent Arc's own `modified`, which
    only bumps on M2M add/remove/clear -- not on a plain field edit to one
    of the linked issues. cache_action_dependent_labels deliberately does
    NOT include ModelLabel.ISSUE/SERIES (see the comment on ArcViewSet):
    both are bumped by update_series_modified_on_issue_save() on *every*
    issue write anywhere on the site, so tying this 24h-TTL cache to either
    would invalidate every Arc's issue_list on essentially any issue edit
    site-wide -- confirmed as a live problem for IssueViewSet's own
    retrieve cache in production. A plain issue field edit showing stale
    here for up to DETAIL_CACHE_TTL is the accepted tradeoff; this test
    guards against re-adding either label and reintroducing that
    regression."""
    url = reverse("api:arc-issue-list", kwargs={"pk": fc_arc.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"][0]["number"] == "1"

    issue_with_arc.number = "2"
    issue_with_arc.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"][0]["number"] == "1"


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


def test_issue_retrieve_after_series_rename_is_accepted_staleness(
    api_client_with_staff_credentials, basic_issue, fc_series, local_cache
):
    """Issue retrieve embeds its Series' name, and renaming a Series
    doesn't bump the owning Issue's `modified` -- but ModelLabel.SERIES is
    deliberately NOT one of IssueViewSet's cache_detail_dependent_labels
    (see the comment there): that counter is also bumped by
    update_series_modified_on_issue_save() on every issue write anywhere,
    so tying Issue's detail cache to it invalidated every cached issue
    detail response on essentially any issue edit site-wide (confirmed in
    production -- an unrelated issue write elsewhere flipped an
    otherwise-stable X-Cache HIT to a MISS). A Series rename showing stale
    here for up to DETAIL_CACHE_TTL is the accepted tradeoff; this test
    guards against re-adding SERIES and reintroducing that regression."""
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["series"]["name"] == "Final Crisis"

    fc_series.name = "Final Crisis Renamed"
    fc_series.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["series"]["name"] == "Final Crisis"


def test_issue_retrieve_after_publisher_rename_is_not_stale(
    api_client_with_staff_credentials, basic_issue, dc_comics, local_cache
):
    """Issue retrieve embeds its (Series') Publisher's name via
    cache_detail_dependent_labels -- unlike SERIES, nothing else bumps
    PUBLISHER's version counter, so this dependency doesn't have the same
    cross-contamination problem and should still catch a rename."""
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["publisher"]["name"] == "DC Comics"

    dc_comics.name = "DC Comics Renamed"
    dc_comics.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["publisher"]["name"] == "DC Comics Renamed"


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


def test_arc_issue_list_after_series_rename_is_accepted_staleness(
    api_client_with_staff_credentials, issue_with_arc, fc_arc, fc_series, local_cache
):
    """issue_list nests each issue's Series name, and renaming the Series
    doesn't bump the parent Arc's `modified` -- but ModelLabel.SERIES is
    deliberately not tied to this 24h-TTL cache either, for the same
    reason as ModelLabel.ISSUE (see the comment on ArcViewSet): it's
    bumped on every issue write anywhere on the site, not just renames."""
    url = reverse("api:arc-issue-list", kwargs={"pk": fc_arc.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"][0]["series"]["name"] == "Final Crisis"

    fc_series.name = "Final Crisis Renamed"
    fc_series.save()

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["results"][0]["series"]["name"] == "Final Crisis"


def test_issue_retrieve_reflects_character_added(
    api_client_with_staff_credentials, basic_issue, superman, local_cache
):
    """Issue retrieve embeds `characters`, and adding one doesn't touch
    Issue.modified via Character's auto_now -- update_related_modified now
    bumps the specific Issue's own `modified` too (in addition to the
    Character's, for its issue_list cache), scoped by pk so it can't
    cross-contaminate other issues."""
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["characters"] == []

    basic_issue.characters.add(superman)

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["characters"]) == 1
    assert resp.json()["characters"][0]["name"] == "Superman"


def test_issue_retrieve_reflects_character_removed(
    api_client_with_staff_credentials, issue_with_arc, superman, local_cache
):
    url = reverse("api:issue-detail", kwargs={"pk": issue_with_arc.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["characters"]) == 1

    issue_with_arc.characters.remove(superman)

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["characters"] == []


def test_issue_retrieve_reflects_universe_added(
    api_client_with_staff_credentials, basic_issue, earth_2_universe, local_cache
):
    """Issue.universes has no issue_list-style consumer on the Universe
    side, so update_issue_modified_on_universe_change only needs to (and
    does) bump the Issue's own `modified`."""
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["universes"] == []

    basic_issue.universes.add(earth_2_universe)

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["universes"]) == 1


def test_issue_retrieve_reflects_reprint_added(
    api_client_with_staff_credentials, basic_issue, create_user, fc_series, local_cache
):
    """Issue.reprints is a symmetric self-referential M2M; both the issue
    the .add() was called through and the other issue involved should
    invalidate."""
    user = create_user()
    other_issue = Issue.objects.create(
        series=fc_series,
        number="2",
        slug="final-crisis-2",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )

    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["reprints"] == []

    basic_issue.reprints.add(other_issue)

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["reprints"]) == 1


def test_issue_retrieve_reflects_variant_added(
    api_client_with_staff_credentials, basic_issue, local_cache
):
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["variants"] == []

    Variant.objects.create(issue=basic_issue, image="", name="Foil Variant")

    resp = api_client_with_staff_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["variants"]) == 1
    assert resp.json()["variants"][0]["name"] == "Foil Variant"


def test_issue_retrieve_x_cache_header(api_client_with_credentials, basic_issue, local_cache):
    url = reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"

    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "HIT"


def test_arc_list_x_cache_header(api_client_with_credentials, wwh_arc, local_cache):
    url = reverse("api:arc-list")
    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"

    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "HIT"


def test_arc_issue_list_x_cache_header(
    api_client_with_credentials, issue_with_arc, fc_arc, local_cache
):
    url = reverse("api:arc-issue-list", kwargs={"pk": fc_arc.pk})
    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"

    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "HIT"


def test_arc_retrieve_does_not_poison_issue_list_cache(
    api_client_with_credentials, issue_with_arc, fc_arc, local_cache
):
    """retrieve and issue_list are both cached via detail_cache_key() keyed
    on (cache_model_label, pk, modified, *dependent_labels). ArcViewSet sets
    neither cache_detail_dependent_labels nor cache_action_dependent_labels,
    so without an action discriminator in the key, the two endpoints would
    collide on the same Redis entry -- whichever ran first would get served
    back for the other, wrong response shape and all (confirmed live: a
    /issue_list/ request returning the arc's own detail payload)."""
    detail_url = reverse("api:arc-detail", kwargs={"pk": fc_arc.pk})
    resp = api_client_with_credentials.get(detail_url)
    assert resp.status_code == status.HTTP_200_OK

    issue_list_url = reverse("api:arc-issue-list", kwargs={"pk": fc_arc.pk})
    resp = api_client_with_credentials.get(issue_list_url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"
    body = resp.json()
    assert "results" in body
    assert body["results"][0]["number"] == "1"


def test_arc_issue_list_pagination_is_not_poisoned_across_pages(
    api_client_with_credentials, issue_with_arc, fc_arc, fc_series, monkeypatch, local_cache
):
    """issue_list's cache key must include the request's query string, since
    ?page=1 and ?page=2 return different data for the same (pk, modified)."""
    # PageNumberPagination.page_size is read from api_settings.PAGE_SIZE at
    # class-definition time, not per-request, so overriding
    # settings.REST_FRAMEWORK here wouldn't affect it -- patch the class
    # attribute directly instead.
    monkeypatch.setattr(PageNumberPagination, "page_size", 1)

    second_issue = Issue.objects.create(
        series=fc_series,
        number="2",
        slug="final-crisis-2",
        cover_date=timezone.now().date(),
        edited_by=issue_with_arc.edited_by,
        created_by=issue_with_arc.created_by,
    )
    second_issue.arcs.add(fc_arc)

    url = reverse("api:arc-issue-list", kwargs={"pk": fc_arc.pk})
    page_one = api_client_with_credentials.get(url, {"page": 1})
    assert page_one.status_code == status.HTTP_200_OK
    assert [r["number"] for r in page_one.json()["results"]] == ["1"]

    page_two = api_client_with_credentials.get(url, {"page": 2})
    assert page_two.status_code == status.HTTP_200_OK
    assert [r["number"] for r in page_two.json()["results"]] == ["2"]


def test_arc_retrieve_resource_url_is_not_poisoned_across_hosts(
    api_client_with_credentials, fc_arc, settings, local_cache
):
    """resource_url is built from request.build_absolute_uri(), so the
    cache key must include the request's scheme/host -- otherwise a
    response cached while serving one hostname gets that hostname baked
    into resource_url for every other hostname the API is also reachable
    under."""
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, "other.example"]
    url = reverse("api:arc-detail", kwargs={"pk": fc_arc.pk})

    resp = api_client_with_credentials.get(url, HTTP_HOST="testserver")
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"
    assert resp.json()["resource_url"].startswith("http://testserver/")

    resp = api_client_with_credentials.get(url, HTTP_HOST="other.example")
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"
    assert resp.json()["resource_url"].startswith("http://other.example/")


def test_character_retrieve_does_not_poison_issue_list_cache(
    api_client_with_credentials, issue_with_arc, superman, local_cache
):
    detail_url = reverse("api:character-detail", kwargs={"pk": superman.pk})
    resp = api_client_with_credentials.get(detail_url)
    assert resp.status_code == status.HTTP_200_OK

    issue_list_url = reverse("api:character-issue-list", kwargs={"pk": superman.pk})
    resp = api_client_with_credentials.get(issue_list_url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"
    body = resp.json()
    assert "results" in body
    assert body["results"][0]["number"] == "1"


def test_team_retrieve_does_not_poison_issue_list_cache(
    api_client_with_credentials, multi_story_issue, teen_titans, local_cache
):
    detail_url = reverse("api:team-detail", kwargs={"pk": teen_titans.pk})
    resp = api_client_with_credentials.get(detail_url)
    assert resp.status_code == status.HTTP_200_OK

    issue_list_url = reverse("api:team-issue-list", kwargs={"pk": teen_titans.pk})
    resp = api_client_with_credentials.get(issue_list_url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"
    body = resp.json()
    assert "results" in body
    assert body["results"][0]["number"] == "3"


def test_publisher_series_list_x_cache_header(
    api_client_with_credentials, dc_comics, fc_series, local_cache
):
    url = reverse("api:publisher-series-list", kwargs={"pk": dc_comics.pk})
    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "MISS"

    resp = api_client_with_credentials.get(url)
    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-Cache"] == "HIT"


def test_uncached_viewset_gets_no_x_cache_header(api_client_with_credentials, local_cache):
    """PullListViewSet uses plain mixins.ListModelMixin, not
    CachedListModelMixin -- confirms the header is only added on the paths
    that actually go through the response cache, not stamped unconditionally."""
    resp = api_client_with_credentials.get(reverse("api:pull_list-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "X-Cache" not in resp


def test_user_scoped_viewsets_are_not_list_cached():
    """CollectionViewSet/PullListViewSet/WishListViewSet are user-scoped
    (get_queryset filters by request.user) -- they must never use
    CachedListModelMixin, since a shared list cache key would serve one
    user's private data to another. This is a cheap regression guard for
    that intentional exclusion; see api/views.py."""
    for viewset in (CollectionViewSet, PullListViewSet, WishListViewSet):
        assert getattr(viewset, "cache_model_label", None) is None
