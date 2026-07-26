import base64

import pytest
from django.urls import reverse
from rest_framework import status

from users.models import ApiToken


@pytest.mark.django_db
def test_token_authentication_succeeds(api_client_with_token_credentials):
    api_client, _user = api_client_with_token_credentials
    resp = api_client.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK


@pytest.mark.django_db
def test_missing_credentials_returns_401(api_client):
    resp = api_client.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_bad_token_returns_401(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")
    resp = api_client.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_revoked_token_returns_401(create_user, api_client):
    user = create_user()
    instance, token = ApiToken.objects.create(user=user, name="test")
    instance.delete()

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_basic_authentication_still_works(create_user, api_client, test_password):
    user = create_user()
    credentials = base64.b64encode(f"{user.username}:{test_password}".encode()).decode()

    api_client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")
    resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
