"""Tests for the Wish List API."""

from django.urls import reverse
from rest_framework import status

from user_collection.models import CollectionItem
from wish_list.models import WishListItem


def test_unauthenticated_list_requires_auth(api_client):
    resp = api_client.get(reverse("api:wish_list-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_user_gets_own_wish_list(api_client, wish_list_user, public_wish_list):
    api_client.force_authenticate(user=wish_list_user)
    resp = api_client.get(reverse("api:wish_list-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == public_wish_list.pk


def test_other_user_cannot_see_wish_list(
    api_client, wish_list_user, other_wish_list_user, public_wish_list
):
    api_client.force_authenticate(user=other_wish_list_user)
    resp = api_client.get(reverse("api:wish_list-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_items_action_returns_items(api_client, wish_list_user, wish_list_item, wish_list_item_2):
    api_client.force_authenticate(user=wish_list_user)
    resp = api_client.get(reverse("api:wish_list-items"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 2


def test_items_action_unauthenticated(api_client):
    resp = api_client.get(reverse("api:wish_list-items"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_add_item_action_creates_item(
    api_client, wish_list_user, public_wish_list, wish_list_issue
):
    api_client.force_authenticate(user=wish_list_user)
    resp = api_client.post(
        reverse("api:wish_list-add-item"),
        data={"issue_id": wish_list_issue.pk, "priority": 1},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert WishListItem.objects.filter(wish_list=public_wish_list, issue=wish_list_issue).exists()


def test_add_item_duplicate_returns_200(
    api_client, wish_list_user, public_wish_list, wish_list_item, wish_list_issue
):
    api_client.force_authenticate(user=wish_list_user)
    resp = api_client.post(
        reverse("api:wish_list-add-item"),
        data={"issue_id": wish_list_issue.pk},
    )
    assert resp.status_code == status.HTTP_200_OK


def test_add_item_invalid_issue_returns_400(api_client, wish_list_user, public_wish_list):
    api_client.force_authenticate(user=wish_list_user)
    resp = api_client.post(
        reverse("api:wish_list-add-item"),
        data={"issue_id": 999999},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_acquire_item_creates_collection_item(api_client, wish_list_user, wish_list_item):
    api_client.force_authenticate(user=wish_list_user)
    url = reverse("api:wish_list-acquire-item", kwargs={"item_pk": wish_list_item.pk})
    resp = api_client.post(url, data={"purchase_store": "LCS"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["created"] is True
    wish_list_item.refresh_from_db()
    assert wish_list_item.status == WishListItem.Status.ACQUIRED
    assert CollectionItem.objects.filter(user=wish_list_user, issue=wish_list_item.issue).exists()


def test_acquire_item_already_in_collection(api_client, wish_list_user, wish_list_item):
    CollectionItem.objects.create(user=wish_list_user, issue=wish_list_item.issue)
    api_client.force_authenticate(user=wish_list_user)
    url = reverse("api:wish_list-acquire-item", kwargs={"item_pk": wish_list_item.pk})
    resp = api_client.post(url, data={})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["created"] is False


def test_acquire_item_other_user_gets_404(api_client, other_wish_list_user, wish_list_item):
    api_client.force_authenticate(user=other_wish_list_user)
    url = reverse("api:wish_list-acquire-item", kwargs={"item_pk": wish_list_item.pk})
    resp = api_client.post(url, data={})
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_remove_item_returns_204(api_client, wish_list_user, wish_list_item):
    api_client.force_authenticate(user=wish_list_user)
    url = reverse("api:wish_list-remove-item", kwargs={"item_pk": wish_list_item.pk})
    resp = api_client.delete(url)
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not WishListItem.objects.filter(pk=wish_list_item.pk).exists()


def test_remove_item_other_user_gets_404(api_client, other_wish_list_user, wish_list_item):
    api_client.force_authenticate(user=other_wish_list_user)
    url = reverse("api:wish_list-remove-item", kwargs={"item_pk": wish_list_item.pk})
    resp = api_client.delete(url)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_add_item_unauthenticated(api_client, wish_list_issue):
    resp = api_client.post(reverse("api:wish_list-add-item"), data={"issue_id": wish_list_issue.pk})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
