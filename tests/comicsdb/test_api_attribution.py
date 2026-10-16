import uuid
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from drf_spectacular.generators import SchemaGenerator
from rest_framework import status

from api.cache import ModelLabel, get_model_version
from api.v1_0.serializers.attribution import SOURCE_NAMES
from comicsdb.models import Attribution, Character, Publisher, Rating

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
    # Ordered by creation within one object, so the response is stable across cache misses.
    assert resp.json()["attribution"] == [
        {"source": "Wikipedia", "url": WIKI_URL},
        {"source": "Marvel", "url": MARVEL_URL},
    ]


def test_every_attribution_source_has_an_api_name():
    assert set(SOURCE_NAMES) == set(Attribution.Source)


@pytest.mark.parametrize(("fixture_name", "basename"), ATTRIBUTED_RESOURCES)
def test_list_does_not_include_attribution(
    request, api_client_with_credentials, local_cache, fixture_name, basename
):
    obj = request.getfixturevalue(fixture_name)
    obj.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)

    resp = api_client_with_credentials.get(reverse(f"api:{basename}-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "attribution" not in resp.json()["results"][0]


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


def test_attribution_save_does_not_reread_its_row(batman, local_cache):
    created = batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    attribution = Attribution.objects.get(pk=created.pk)
    attribution.url = MARVEL_URL

    with CaptureQueriesContext(connection) as ctx:
        attribution.save()

    assert not [
        q
        for q in ctx.captured_queries
        if q["sql"].startswith("SELECT") and "comicsdb_attribution" in q["sql"]
    ]


def test_attribution_save_does_not_query_content_type(batman, local_cache):
    attribution = batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    attribution = Attribution.objects.get(pk=attribution.pk)  # fresh instance, no cached FK

    with CaptureQueriesContext(connection) as ctx:
        attribution.save()
        attribution.delete()

    assert not [q for q in ctx.captured_queries if "django_content_type" in q["sql"]]


def test_attribution_raw_save_skips_parent_bump(batman, local_cache):
    attribution = Attribution(
        source=Attribution.Source.WIKIPEDIA, url=WIKI_URL, content_object=batman
    )
    with patch("comicsdb.signals._touch_attribution_parent") as touch:
        attribution.save_base(raw=True)
    touch.assert_not_called()


def test_parent_delete_skips_attribution_parent_bump(batman, local_cache):
    batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    batman.attribution.create(source=Attribution.Source.MARVEL, url=MARVEL_URL)

    with patch("comicsdb.signals._touch_attribution_parent") as touch:
        batman.delete()

    touch.assert_not_called()
    assert not Attribution.objects.exists()


def test_attribution_queryset_delete_bumps_parent(batman, local_cache):
    batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    past = timezone.now() - timedelta(days=1)
    Character.objects.filter(pk=batman.pk).update(modified=past)

    batman.attribution.all().delete()

    batman.refresh_from_db()
    assert batman.modified > past


def test_attribution_on_model_without_modified_saves(db, local_cache):
    rating = Rating.objects.create(name="Test Rating")

    attribution = Attribution.objects.create(
        source=Attribution.Source.WIKIPEDIA, url=WIKI_URL, content_object=rating
    )
    attribution.delete()


def test_create_view_saves_parent_once(auto_login_user, local_cache):
    client, _ = auto_login_user()
    data = {
        "name": "Ahoy Comics",
        "country": "US",
        "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
        "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
        "comicsdb-attribution-content_type-object_id-0-source": "W",
        "comicsdb-attribution-content_type-object_id-0-url": WIKI_URL,
    }

    resp = client.post(reverse("publisher:create"), data=data)

    assert resp.status_code == status.HTTP_302_FOUND
    ahoy = Publisher.objects.get(name="Ahoy Comics")
    assert resp.url == ahoy.get_absolute_url()
    assert ahoy.attribution.count() == 1
    # One history row per save.
    assert ahoy.history.count() == 1


def test_attribution_queryset_delete_bumps_each_parent_once(batman, superman, local_cache):
    batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    batman.attribution.create(source=Attribution.Source.MARVEL, url=MARVEL_URL)
    superman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)

    with patch("comicsdb.signals._touch_attribution_parent") as touch:
        Attribution.objects.all().delete()

    assert touch.call_count == 2


def test_schema_names_attribution_source_enum(db):
    schemas = SchemaGenerator().get_schema(request=None, public=True)["components"]["schemas"]
    assert schemas["AttributionSourceEnum"]["enum"] == list(SOURCE_NAMES.values())
    assert "SourceEnum" not in schemas


def test_unknown_source_code_falls_back_to_stored_value(
    api_client_with_credentials, batman, local_cache
):
    # The model only enforces choices in forms, so a raw write can store anything.
    attribution = batman.attribution.create(source=Attribution.Source.WIKIPEDIA, url=WIKI_URL)
    Attribution.objects.filter(pk=attribution.pk).update(source="X")

    resp = api_client_with_credentials.get(reverse("api:character-detail", args=(batman.pk,)))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["attribution"] == [{"source": "X", "url": WIKI_URL}]
