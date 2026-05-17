"""Tests for the Pull List API."""

from django.urls import reverse
from rest_framework import status

from pull_list.models import PullListSeries


def test_unauthenticated_list_requires_auth(api_client):
    resp = api_client.get(reverse("api:pull_list-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_user_gets_own_pull_list(api_client, pull_list_user, pull_list):
    api_client.force_authenticate(user=pull_list_user)
    resp = api_client.get(reverse("api:pull_list-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == pull_list.pk


def test_other_user_cannot_see_pull_list(
    api_client, pull_list_user, other_pull_list_user, pull_list
):
    api_client.force_authenticate(user=other_pull_list_user)
    resp = api_client.get(reverse("api:pull_list-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_series_action_returns_series(
    api_client, pull_list_user, pull_list_with_series, pull_list_series
):
    api_client.force_authenticate(user=pull_list_user)
    resp = api_client.get(reverse("api:pull_list-series"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["series"]["id"] == pull_list_series.pk


def test_series_action_unauthenticated(api_client):
    resp = api_client.get(reverse("api:pull_list-series"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_add_series_action_creates_entry(api_client, pull_list_user, pull_list, pull_list_series):
    api_client.force_authenticate(user=pull_list_user)
    resp = api_client.post(
        reverse("api:pull_list-add-series"), data={"series_id": pull_list_series.pk}
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert PullListSeries.objects.filter(pull_list=pull_list, series=pull_list_series).exists()


def test_add_series_already_present_returns_200(
    api_client, pull_list_user, pull_list_with_series, pull_list_series
):
    api_client.force_authenticate(user=pull_list_user)
    resp = api_client.post(
        reverse("api:pull_list-add-series"), data={"series_id": pull_list_series.pk}
    )
    assert resp.status_code == status.HTTP_200_OK


def test_add_series_missing_id_returns_400(api_client, pull_list_user, pull_list):
    api_client.force_authenticate(user=pull_list_user)
    resp = api_client.post(reverse("api:pull_list-add-series"), data={})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_add_series_invalid_id_returns_404(api_client, pull_list_user, pull_list):
    api_client.force_authenticate(user=pull_list_user)
    resp = api_client.post(reverse("api:pull_list-add-series"), data={"series_id": 999999})
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_remove_series_returns_204(
    api_client, pull_list_user, pull_list_with_series, pull_list_series
):
    api_client.force_authenticate(user=pull_list_user)
    url = reverse("api:pull_list-remove-series", kwargs={"series_pk": pull_list_series.pk})
    resp = api_client.delete(url)
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not PullListSeries.objects.filter(
        pull_list=pull_list_with_series, series=pull_list_series
    ).exists()


def test_remove_series_not_on_list_returns_404(
    api_client, pull_list_user, pull_list, pull_list_series
):
    api_client.force_authenticate(user=pull_list_user)
    url = reverse("api:pull_list-remove-series", kwargs={"series_pk": pull_list_series.pk})
    resp = api_client.delete(url)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_add_series_unauthenticated(api_client, pull_list_series):
    resp = api_client.post(
        reverse("api:pull_list-add-series"), data={"series_id": pull_list_series.pk}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
