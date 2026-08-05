from django.urls import reverse
from rest_framework import status


def test_whoami_returns_authenticated_username(api_client, create_user):
    user = create_user(username="wanda")
    api_client.force_authenticate(user=user)

    resp = api_client.get(reverse("api:whoami"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp.data == {"username": "wanda"}


def test_whoami_unauthorized(api_client):
    resp = api_client.get(reverse("api:whoami"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
