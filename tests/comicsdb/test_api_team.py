import pytest
from django.urls import reverse
from rest_framework import status


@pytest.fixture
def create_team_data(john_byrne, earth_2_universe):
    return {
        "name": "The Crazies",
        "desc": "Blah Blah",
        "creators": [john_byrne.id],
        "universes": [earth_2_universe.id],
    }


@pytest.fixture
def create_put_data():
    return {"name": "Still Crazy", "slug": "still-crazy"}


# Post Tests
def test_unauthorized_post_url(db, api_client, create_team_data):
    resp = api_client.post(reverse("api:team-list"), data=create_team_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_team_data):
    resp = api_client_with_credentials.post(reverse("api:team-list"), data=create_team_data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_post_url(db, api_client_with_staff_credentials, create_team_data):
    resp = api_client_with_staff_credentials.post(reverse("api:team-list"), data=create_team_data)
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["name"] == create_team_data["name"]
    assert resp.data["desc"] == create_team_data["desc"]
    assert resp.data["creators"] == create_team_data["creators"]
    assert resp.data["universes"] == create_team_data["universes"]


# Put Tests
def test_unauthorized_put_url(db, api_client, avengers, create_put_data):
    resp = api_client.put(
        reverse("api:team-detail", kwargs={"pk": avengers.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_put_url(api_client_with_credentials, avengers, create_put_data):
    resp = api_client_with_credentials.put(
        reverse("api:team-detail", kwargs={"pk": avengers.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_put_url(api_client_with_staff_credentials, avengers, create_put_data):
    resp = api_client_with_staff_credentials.patch(
        reverse("api:team-detail", kwargs={"pk": avengers.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_200_OK


# Regular Tests
def test_view_url_accessible_by_name(api_client_with_credentials, avengers, teen_titans):
    resp = api_client_with_credentials.get(reverse("api:team-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client, avengers, teen_titans):
    resp = api_client.get(reverse("api:team-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_valid_single_team(api_client_with_credentials, avengers):
    resp = api_client_with_credentials.get(reverse("api:team-detail", kwargs={"pk": avengers.pk}))
    assert resp.status_code == status.HTTP_200_OK


def test_get_invalid_single_team(api_client_with_credentials):
    response = api_client_with_credentials.get(reverse("api:team-detail", kwargs={"pk": "10"}))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unauthorized_detail_view_url(api_client, avengers):
    response = api_client.get(reverse("api:team-detail", kwargs={"pk": avengers.pk}))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
