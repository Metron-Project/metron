from django.urls import reverse
from rest_framework import status

from api.v1_0.serializers import RoleSerializer


def test_view_url_accessible_by_name(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:role-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_role_list_view(api_client_with_credentials, writer):
    response = api_client_with_credentials.get(reverse("api:role-list"))
    serializer = RoleSerializer(writer)
    assert response.data["count"] == 1
    assert response.data["next"] is None
    assert response.data["previous"] is None
    assert response.data["results"][0] == serializer.data
    assert response.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client):
    resp = api_client.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
