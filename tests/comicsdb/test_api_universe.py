import pytest
from django.urls import reverse
from rest_framework import status


@pytest.fixture
def create_universe_data(dc_comics):
    return {
        "publisher": dc_comics.id,
        "name": "Dark Multiverse: Devastator",
        "designation": "Earth -1",
        "desc": "Home to Devastator",
    }


@pytest.fixture
def create_put_data():
    return {"name": "Spidey's Dark Turn", "slug": "spideys-dark-turn", "desc": "I've changed!"}


# Post Tests
def test_unauthorized_post_url(db, api_client, create_universe_data):
    resp = api_client.post(reverse("api:universe-list"), data=create_universe_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_universe_data):
    resp = api_client_with_credentials.post(reverse("api:universe-list"), data=create_universe_data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_post_url(db, api_client_with_staff_credentials, create_universe_data):
    resp = api_client_with_staff_credentials.post(
        reverse("api:universe-list"), data=create_universe_data
    )
    assert resp.status_code == status.HTTP_201_CREATED


# Put Tests
def test_unauthorized_put_url(db, api_client, earth_2_universe, create_put_data):
    resp = api_client.put(
        reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk}),
        data=create_put_data,
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_put_url(api_client_with_credentials, earth_2_universe, create_put_data):
    resp = api_client_with_credentials.put(
        reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk}),
        data=create_put_data,
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_put_url(api_client_with_staff_credentials, earth_2_universe, create_put_data):
    resp = api_client_with_staff_credentials.patch(
        reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk}),
        data=create_put_data,
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data.get("name") == create_put_data.get("name")
    assert resp.data.get("desc") == create_put_data.get("desc")


# Regular Tests
def test_view_url_accessible_by_name(api_client_with_credentials, earth_2_universe):
    resp = api_client_with_credentials.get(reverse("api:universe-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client, earth_2_universe):
    resp = api_client.get(reverse("api:universe-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_valid_single_universe(api_client_with_credentials, earth_2_universe):
    resp = api_client_with_credentials.get(
        reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk})
    )
    assert resp.status_code == status.HTTP_200_OK


def test_get_invalid_single_universe(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:universe-detail", kwargs={"pk": "10"}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_unauthorized_detail_view_url(api_client, earth_2_universe):
    resp = api_client.get(reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk}))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
