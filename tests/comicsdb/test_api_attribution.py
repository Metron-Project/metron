import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.cache import ModelLabel, get_model_version
from comicsdb.models import Attribution, Character

# (fixture name, API basename) for every resource whose detail response embeds attribution.
ATTRIBUTED_RESOURCES = [
    ("wwh_arc", "arc"),
    ("batman", "character"),
    ("john_byrne", "creator"),
    ("vertigo_imprint", "imprint"),
    ("basic_issue", "issue"),
    ("dc_comics", "publisher"),
    ("fc_series", "series"),
    ("teen_titans", "team"),
    ("earth_2_universe", "universe"),
]

WIKI_URL = "https://en.wikipedia.org/wiki/Example"
MARVEL_URL = "https://www.marvel.com/characters/example"


@pytest.fixture
def local_cache():
    """Isolate the response cache from concurrent xdist workers sharing Redis."""
    test_cache = LocMemCache(f"test-api-attribution-{uuid.uuid4()}", {})
    with patch("api.views.cache", test_cache), patch("api.cache.cache", test_cache):
        yield test_cache


@pytest.mark.parametrize(("fixture_name", "basename"), ATTRIBUTED_RESOURCES)
def test_detail_attribution_is_empty_list_by_default(
    request, api_client_with_credentials, local_cache, fixture_name, basename
):
    obj = request.getfixturevalue(fixture_name)
    resp = api_client_with_credentials.get(reverse(f"api:{basename}-detail", args=(obj.pk,)))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["attribution"] == []


@pytest.mark.parametrize(("fixture_name", "basename"), ATTRIBUTED_RESOURCES)
def test_detail_attribution_returns_source_label_and_url(
    request, api_client_with_credentials, local_cache, fixture_name, basename
):
    obj = request.getfixturevalue(fixture_name)
    obj.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    obj.attribution.create(source=Attribution.Source.MARVEL, url=MARVEL_URL)

    resp = api_client_with_credentials.get(reverse(f"api:{basename}-detail", args=(obj.pk,)))
    assert resp.status_code == status.HTTP_200_OK
    assert sorted(resp.json()["attribution"], key=lambda a: a["source"]) == [
        {"source": "Marvel", "url": MARVEL_URL},
        {"source": "Wikipedia", "url": WIKI_URL},
    ]


@pytest.mark.parametrize(("fixture_name", "basename"), ATTRIBUTED_RESOURCES)
def test_list_does_not_include_attribution(
    request, api_client_with_credentials, local_cache, fixture_name, basename
):
    obj = request.getfixturevalue(fixture_name)
    obj.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)

    resp = api_client_with_credentials.get(reverse(f"api:{basename}-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "attribution" not in resp.json()["results"][0]


@pytest.mark.parametrize(("fixture_name", "basename"), ATTRIBUTED_RESOURCES)
def test_detail_attribution_query_count_is_constant(
    request, api_client_with_credentials, local_cache, fixture_name, basename
):
    obj = request.getfixturevalue(fixture_name)
    url = reverse(f"api:{basename}-detail", args=(obj.pk,))
    obj.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)

    local_cache.clear()
    with CaptureQueriesContext(connection) as one:
        api_client_with_credentials.get(url)

    obj.attribution.create(source=Attribution.Source.MARVEL, url=MARVEL_URL)
    obj.attribution.create(source=Attribution.Source.GCD, url="https://www.comics.org/x/")

    local_cache.clear()
    with CaptureQueriesContext(connection) as three:
        resp = api_client_with_credentials.get(url)

    assert len(resp.json()["attribution"]) == 3
    assert len(three) == len(one)


def test_attribution_add_busts_detail_cache(api_client_with_credentials, batman, local_cache):
    url = reverse("api:character-detail", args=(batman.pk,))
    assert api_client_with_credentials.get(url).json()["attribution"] == []

    batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)

    resp = api_client_with_credentials.get(url)
    assert resp.json()["attribution"] == [{"source": "Wikipedia", "url": WIKI_URL}]


def test_attribution_edit_busts_detail_cache(api_client_with_credentials, batman, local_cache):
    attribution = batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    url = reverse("api:character-detail", args=(batman.pk,))
    assert api_client_with_credentials.get(url).json()["attribution"][0]["url"] == WIKI_URL

    attribution.source = Attribution.Source.MARVEL
    attribution.url = MARVEL_URL
    attribution.save()

    resp = api_client_with_credentials.get(url)
    assert resp.json()["attribution"] == [{"source": "Marvel", "url": MARVEL_URL}]


def test_attribution_delete_busts_detail_cache(api_client_with_credentials, batman, local_cache):
    attribution = batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    url = reverse("api:character-detail", args=(batman.pk,))
    assert len(api_client_with_credentials.get(url).json()["attribution"]) == 1

    attribution.delete()

    assert api_client_with_credentials.get(url).json()["attribution"] == []


def test_attribution_change_updates_last_modified(api_client_with_credentials, batman, local_cache):
    # Last-Modified has one-second resolution; backdate so the bump is visible.
    Character.objects.filter(pk=batman.pk).update(modified=timezone.now() - timedelta(days=1))
    url = reverse("api:character-detail", args=(batman.pk,))
    last_modified = api_client_with_credentials.get(url)["Last-Modified"]
    stale = api_client_with_credentials.get(url, HTTP_IF_MODIFIED_SINCE=last_modified)
    assert stale.status_code == status.HTTP_304_NOT_MODIFIED

    batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)

    resp = api_client_with_credentials.get(url, HTTP_IF_MODIFIED_SINCE=last_modified)
    assert resp.status_code == status.HTTP_200_OK
    assert len(resp.json()["attribution"]) == 1


def test_attribution_change_bumps_parent_modified_and_cache_version(batman, local_cache):
    past = timezone.now() - timedelta(days=1)
    Character.objects.filter(pk=batman.pk).update(modified=past)
    before = get_model_version(ModelLabel.CHARACTER)

    attribution = batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    batman.refresh_from_db()
    assert batman.modified > past
    assert get_model_version(ModelLabel.CHARACTER) == before + 1

    Character.objects.filter(pk=batman.pk).update(modified=past)
    attribution.delete()
    batman.refresh_from_db()
    assert batman.modified > past
    assert get_model_version(ModelLabel.CHARACTER) == before + 2
