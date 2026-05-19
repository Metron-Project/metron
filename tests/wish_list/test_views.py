"""Tests for wish_list views."""

from django.urls import reverse

from user_collection.models import CollectionItem
from wish_list.models import WishList, WishListItem


# Detail view — authentication
def test_detail_view_requires_login(client):
    resp = client.get(reverse("wish-list:detail"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


def test_detail_view_authenticated_creates_wish_list(client, wish_list_user, test_password):
    client.login(username=wish_list_user.username, password=test_password)
    assert not WishList.objects.filter(user=wish_list_user).exists()
    resp = client.get(reverse("wish-list:detail"))
    assert resp.status_code == 200
    assert WishList.objects.filter(user=wish_list_user).exists()


def test_detail_view_shows_items(client, wish_list_user, test_password, wish_list_item, wish_list):
    client.login(username=wish_list_user.username, password=test_password)
    resp = client.get(reverse("wish-list:detail"))
    assert resp.status_code == 200
    assert wish_list_item.issue.series.name in resp.content.decode()


# Add item via POST
def test_add_item_to_wish_list(client, wish_list_user, test_password, wish_list, wish_list_issue):
    client.login(username=wish_list_user.username, password=test_password)
    resp = client.post(
        reverse("wish-list:detail"),
        data={"issue": wish_list_issue.pk, "priority": 2, "status": "WANTED"},
    )
    assert resp.status_code == 302
    assert WishListItem.objects.filter(wish_list=wish_list, issue=wish_list_issue).exists()


def test_add_duplicate_item_shows_info(
    client, wish_list_user, test_password, wish_list_item, wish_list_issue
):
    client.login(username=wish_list_user.username, password=test_password)
    resp = client.post(
        reverse("wish-list:detail"),
        data={"issue": wish_list_issue.pk, "priority": 1, "status": "WANTED"},
        follow=True,
    )
    assert resp.status_code == 200
    assert WishListItem.objects.filter(issue=wish_list_issue).count() == 1


# Item update view
def test_item_update_requires_owner(
    client, other_wish_list_user, test_password, wish_list_item, wish_list_issue
):
    client.login(username=other_wish_list_user.username, password=test_password)
    resp = client.get(reverse("wish-list:item-update", kwargs={"pk": wish_list_item.pk}))
    assert resp.status_code == 403


# Item delete view
def test_item_delete_owner_can_delete(client, wish_list_user, test_password, wish_list_item):
    client.login(username=wish_list_user.username, password=test_password)
    resp = client.post(reverse("wish-list:item-delete", kwargs={"pk": wish_list_item.pk}))
    assert resp.status_code == 302
    assert not WishListItem.objects.filter(pk=wish_list_item.pk).exists()


def test_item_delete_other_user_cannot_delete(
    client, other_wish_list_user, test_password, wish_list_item
):
    client.login(username=other_wish_list_user.username, password=test_password)
    resp = client.post(reverse("wish-list:item-delete", kwargs={"pk": wish_list_item.pk}))
    assert resp.status_code == 403


# Acquire view
def test_acquire_creates_collection_item(client, wish_list_user, test_password, wish_list_item):
    client.login(username=wish_list_user.username, password=test_password)
    resp = client.post(
        reverse("wish-list:item-acquire", kwargs={"pk": wish_list_item.pk}),
        data={"purchase_store": "Local Comic Shop"},
    )
    assert resp.status_code == 302
    wish_list_item.refresh_from_db()
    assert wish_list_item.status == WishListItem.Status.ACQUIRED
    assert CollectionItem.objects.filter(user=wish_list_user, issue=wish_list_item.issue).exists()


def test_acquire_other_user_cannot_acquire(
    client, other_wish_list_user, test_password, wish_list_item
):
    client.login(username=other_wish_list_user.username, password=test_password)
    resp = client.post(reverse("wish-list:item-acquire", kwargs={"pk": wish_list_item.pk}), data={})
    assert resp.status_code == 403
