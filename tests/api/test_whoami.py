import base64

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
def test_whoami_unauthenticated_returns_401(api_client):
    resp = api_client.get(reverse("api:whoami"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_whoami_returns_username(api_client_with_token_credentials):
    api_client, user = api_client_with_token_credentials
    resp = api_client.get(reverse("api:whoami"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["username"] == user.username


@pytest.mark.django_db
def test_whoami_includes_token_expiry_when_authenticated_via_token(
    api_client_with_token_credentials,
):
    api_client, _user = api_client_with_token_credentials
    resp = api_client.get(reverse("api:whoami"))
    # TOKEN_TTL defaults to None (no expiry) in this project's settings.
    assert resp.data["token_expiry"] is None


@pytest.mark.django_db
def test_whoami_token_expiry_is_null_for_basic_auth(create_user, api_client, test_password):
    user = create_user()
    credentials = base64.b64encode(f"{user.username}:{test_password}".encode()).decode()
    api_client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

    resp = api_client.get(reverse("api:whoami"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["token_expiry"] is None


@pytest.mark.django_db
def test_whoami_includes_rate_limit_fields(api_client_with_token_credentials):
    api_client, _user = api_client_with_token_credentials
    resp = api_client.get(reverse("api:whoami"))
    assert resp.status_code == status.HTTP_200_OK
    rate_limit = resp.data["rate_limit"]
    assert set(rate_limit) == {"limit", "used", "remaining", "percent_used"}
