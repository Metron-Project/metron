import pytest
from django.db.models import Count
from django.urls import reverse
from rest_framework import status

from api.v1_0.serializers import SeriesListSerializer
from comicsdb.models import Series


@pytest.fixture
def create_publisher_data():
    return {
        "name": "Soulside",
        "founded": 2021,
        "desc": "Blah Blah",
    }


@pytest.fixture
def create_put_data():
    return {
        "name": "Marvel",
        "slug": "marvel",
        "founded": 1940,
        "wikipedia": "Marvel_Comics",
        "image": "",
    }


# Post Tests
def test_unauthorized_post_url(db, api_client, create_publisher_data):
    resp = api_client.post(reverse("api:publisher-list"), data=create_publisher_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_publisher_data):
    resp = api_client_with_credentials.post(
        reverse("api:publisher-list"), data=create_publisher_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_post_url(db, api_client_with_staff_credentials, create_publisher_data):
    resp = api_client_with_staff_credentials.post(
        reverse("api:publisher-list"), data=create_publisher_data
    )
    assert resp.status_code == status.HTTP_201_CREATED
    # TODO: Fix test to compare data. Specifically the KeyError: 'request' for the
    #       get_resource_url()
    # new_pub = Publisher.objects.get(name=create_publisher_data["name"])
    # serializer = PublisherSerializer(new_pub)
    # assert resp.data == serializer.data


def test_admin_user_post_url_with_alt_names(
    db, api_client_with_staff_credentials, create_publisher_data
):
    create_publisher_data["alt_names"] = ["Soulside Comics"]
    resp = api_client_with_staff_credentials.post(
        reverse("api:publisher-list"), data=create_publisher_data
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["alt_names"] == ["Soulside Comics"]


def test_admin_user_post_url_with_multiple_alt_names(
    db, api_client_with_staff_credentials, create_publisher_data
):
    create_publisher_data["alt_names"] = ["Soulside Comics", "Soulside Publishing", "SSC"]
    resp = api_client_with_staff_credentials.post(
        reverse("api:publisher-list"), data=create_publisher_data
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["alt_names"] == ["Soulside Comics", "Soulside Publishing", "SSC"]


# Put Tests
def test_unauthorized_put_url(db, api_client, marvel, create_put_data):
    resp = api_client.put(
        reverse("api:publisher-detail", kwargs={"pk": marvel.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_put_url(api_client_with_credentials, marvel, create_put_data):
    resp = api_client_with_credentials.put(
        reverse("api:publisher-detail", kwargs={"pk": marvel.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_put_url(api_client_with_staff_credentials, marvel, create_put_data):
    resp = api_client_with_staff_credentials.patch(
        reverse("api:publisher-detail", kwargs={"pk": marvel.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_200_OK
    # TODO: Fix test to compare data. Specifically the KeyError: 'request' for the
    #       get_resource_url()
    # publisher = Publisher.objects.get(pk=marvel.pk)
    # serializer = PublisherSerializer(publisher)
    # assert resp.data == serializer.data


# Regular Tests
def test_view_url_accessible_by_name(api_client_with_credentials, marvel, dc_comics):
    resp = api_client_with_credentials.get(reverse("api:publisher-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client, marvel, dc_comics):
    resp = api_client.get(reverse("api:publisher-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_valid_single_publisher(api_client_with_credentials, dc_comics):
    response = api_client_with_credentials.get(
        reverse("api:publisher-detail", kwargs={"pk": dc_comics.pk})
    )
    assert response.status_code == status.HTTP_200_OK
    # TODO: Fix test to compare data. Specifically the KeyError: 'request' for
    #       the get_resource_url()
    # publisher = Publisher.objects.get(pk=dc_comics.pk)
    # serializer = PublisherSerializer(publisher)
    # assert response.data == serializer.data


def test_get_single_publisher_with_multiple_alt_names(api_client_with_credentials, dc_comics):
    dc_comics.alt_names = ["Detective Comics", "National Comics", "National Periodical"]
    dc_comics.save()

    response = api_client_with_credentials.get(
        reverse("api:publisher-detail", kwargs={"pk": dc_comics.pk})
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["alt_names"] == [
        "Detective Comics",
        "National Comics",
        "National Periodical",
    ]


def test_get_invalid_single_publisher(api_client_with_credentials):
    response = api_client_with_credentials.get(reverse("api:publisher-detail", kwargs={"pk": "10"}))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unauthorized_detail_view_url(api_client, dc_comics):
    response = api_client.get(reverse("api:publisher-detail", kwargs={"pk": dc_comics.pk}))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_filter_by_alt_names(api_client_with_credentials, marvel, dc_comics):
    marvel.alt_names = ["House of Ideas"]
    marvel.save()

    resp = api_client_with_credentials.get("/api/publisher/?alt_names=House")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == marvel.name


def test_filter_by_alt_names_matches_any_of_multiple_values(
    api_client_with_credentials, marvel, dc_comics
):
    marvel.alt_names = ["House of Ideas", "The Mighty Marvel"]
    marvel.save()

    resp = api_client_with_credentials.get("/api/publisher/?alt_names=Mighty")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == marvel.name


def test_filter_by_quick_search(api_client_with_credentials, marvel, dc_comics):
    """Quick search (q) should match either the name or alt_names field."""
    dc_comics.alt_names = ["National Periodical"]
    dc_comics.save()

    # Matches via the primary name field
    resp = api_client_with_credentials.get("/api/publisher/?q=Marvel")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == marvel.name

    # Matches via the alt_names field
    resp = api_client_with_credentials.get("/api/publisher/?q=National+Periodical")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == dc_comics.name


def test_publisher_series_list_view(api_client_with_credentials, dc_comics, fc_series):
    resp = api_client_with_credentials.get(
        reverse("api:publisher-series-list", kwargs={"pk": dc_comics.pk})
    )

    series = (
        Series.objects.filter(pk=fc_series.pk)
        .annotate(num_issues=Count("issues", distinct=True))
        .first()
    )
    serializer = SeriesListSerializer(series)
    assert resp.data["count"] == 1
    assert resp.data["next"] is None
    assert resp.data["previous"] is None
    assert resp.data["results"][0] == serializer.data
    assert resp.status_code == status.HTTP_200_OK
