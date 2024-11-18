import pytest
from django.urls import reverse
from rest_framework import status

from comicsdb.models.creator import Creator
from comicsdb.models.credits import Credits, Role
from comicsdb.models.issue import Issue


@pytest.fixture
def create_data(issue_with_arc: Issue, walter_simonson: Creator, writer: Role):
    return {"issue": issue_with_arc.id, "creator": walter_simonson.id, "role": [writer.id]}


@pytest.fixture
def issue_credit(issue_with_arc: Issue, walter_simonson: Creator, writer: Role) -> Credits:
    c = Credits.objects.create(issue=issue_with_arc, creator=walter_simonson)
    c.role.add(writer)
    return c


@pytest.fixture
def create_put_data(john_byrne):
    return {"creator": john_byrne.id}


# Post Tests
def test_unauthorized_post_url(db, api_client, create_data):
    resp = api_client.post(reverse("api:credits-list"), data=create_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_data):
    resp = api_client_with_credentials.post(reverse("api:credits-list"), data=create_data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_post_url(db, api_client_with_staff_credentials, create_data):
    resp = api_client_with_staff_credentials.post(
        reverse("api:credits-list"), data=create_data
    )
    assert resp.status_code == status.HTTP_201_CREATED


# Put Tests
def test_unauthorized_put_url(db, api_client, issue_credit, create_put_data):
    resp = api_client.put(
        reverse("api:credits-detail", kwargs={"pk": issue_credit.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_put_url(api_client_with_credentials, issue_credit, create_put_data):
    resp = api_client_with_credentials.put(
        reverse("api:credits-detail", kwargs={"pk": issue_credit.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_put_url(api_client_with_staff_credentials, issue_credit, create_put_data):
    resp = api_client_with_staff_credentials.patch(
        reverse("api:credits-detail", kwargs={"pk": issue_credit.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_200_OK
