from datetime import date

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.fixture
def create_creator_data():
    return {
        "name": "A.J. Mendez",
        "desc": "Blah Blah",
        "birth": date(1987, 3, 19),
        "alias": ["AJ Lee"],
    }


@pytest.fixture
def create_put_data():
    return {"alias": ["JB"], "birth": date(1950, 7, 6)}


# Post Tests
def test_unauthorized_post_url(db, api_client, create_creator_data):
    resp = api_client.post(reverse("api:creator-list"), data=create_creator_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_creator_data):
    resp = api_client_with_credentials.post(
        reverse("api:creator-list"), data=create_creator_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_post_url(db, api_client_with_staff_credentials, create_creator_data):
    resp = api_client_with_staff_credentials.post(
        reverse("api:creator-list"), data=create_creator_data
    )
    assert resp.status_code == status.HTTP_201_CREATED


# Put Tests
def test_unauthorized_put_url(db, api_client, john_byrne, create_put_data):
    resp = api_client.put(
        reverse("api:creator-detail", kwargs={"pk": john_byrne.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_put_url(api_client_with_credentials, john_byrne, create_put_data):
    resp = api_client_with_credentials.put(
        reverse("api:creator-detail", kwargs={"pk": john_byrne.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_put_url(api_client_with_staff_credentials, john_byrne, create_put_data):
    resp = api_client_with_staff_credentials.patch(
        reverse("api:creator-detail", kwargs={"pk": john_byrne.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_200_OK


# Regular Tests
def test_view_url_accessible_by_name(api_client_with_credentials, john_byrne, walter_simonson):
    resp = api_client_with_credentials.get(reverse("api:creator-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client, john_byrne, walter_simonson):
    resp = api_client.get(reverse("api:creator-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_valid_single_creator(api_client_with_credentials, john_byrne):
    resp = api_client_with_credentials.get(
        reverse("api:creator-detail", kwargs={"pk": john_byrne.pk})
    )
    assert resp.status_code == status.HTTP_200_OK


def test_get_invalid_single_creator(api_client_with_credentials):
    response = api_client_with_credentials.get(
        reverse("api:creator-detail", kwargs={"pk": "10"})
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unauthorized_detail_view_url(api_client, john_byrne):
    response = api_client.get(reverse("api:creator-detail", kwargs={"pk": john_byrne.pk}))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
