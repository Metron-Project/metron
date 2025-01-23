import operator
from functools import reduce
from urllib.parse import quote_plus

import pytest
from django.db.models import Q
from django.urls import reverse
from rest_framework import status

from api.v1_0.serializers import SeriesListSerializer
from comicsdb.models import Series
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import SeriesType


@pytest.fixture
def create_series_data(single_issue_type: SeriesType, dc_comics: Publisher):
    return {
        "name": "The Wasp",
        "sort_name": "Wasp",
        "volume": 1,
        "desc": "Cancelled series starring the Wasp",
        "year_began": 2023,
        "series_type": single_issue_type.id,
        "status": Series.Status.COMPLETED,
        "publisher": dc_comics.id,
        "imprint": "",  # Empty string or Imprint ID
    }


@pytest.fixture
def create_put_data():
    return {
        "name": "Wasp",
    }


# Post tests
def test_unauthorized_post_url(db, api_client, create_series_data):
    resp = api_client.post(reverse("api:series-list"), data=create_series_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_series_data):
    resp = api_client_with_credentials.post(
        reverse("api:series-list"), data=create_series_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_admin_user_post_url(db, api_client_with_staff_credentials, create_series_data):
    resp = api_client_with_staff_credentials.post(
        reverse("api:series-list"), data=create_series_data
    )
    assert resp.status_code == status.HTTP_201_CREATED


# Put Tests
def test_unauthorized_put_url(db, api_client, fc_series, create_put_data):
    resp = api_client.put(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_put_url(api_client_with_credentials, fc_series, create_put_data):
    resp = api_client_with_credentials.put(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_staff_user_put_url(api_client_with_staff_credentials, fc_series, create_put_data):
    resp = api_client_with_staff_credentials.patch(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_200_OK


# Regular Tests
def test_view_url_accessible_by_name(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:series-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client):
    resp = api_client.get(reverse("api:series-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_valid_single_issue(api_client_with_credentials, fc_series, issue_with_arc):
    resp = api_client_with_credentials.get(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    # series = Series.objects.get(pk=fc_series.pk)
    # serializer = SeriesReadSerializer(series)
    # assert resp.data == serializer.data


def test_unauthorized_detail_view_url(api_client, fc_series):
    response = api_client.get(reverse("api:series-detail", kwargs={"pk": fc_series.pk}))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_series_search(api_client_with_credentials, bat_sups_series, fc_series):
    search_term = "batman superman"
    resp = api_client_with_credentials.get(f"/api/series/?name={quote_plus(search_term)}")
    expected = Series.objects.filter(
        reduce(operator.and_, (Q(name__icontains=q) for q in search_term.split()))
    )
    serializer = SeriesListSerializer(expected, many=True)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["results"] == serializer.data
