"""Tests for wish_list models."""

import pytest
from django.db import IntegrityError

from wish_list.models import WishList, WishListItem


def test_wish_list_str(wish_list, wish_list_user):
    assert str(wish_list) == f"{wish_list_user.username}'s Wish List"


def test_wish_list_item_str(wish_list_item, wish_list_user):
    s = str(wish_list_item)
    assert wish_list_user.username in s
    assert "Wanted" in s


def test_wish_list_one_per_user(wish_list_user, wish_list):
    with pytest.raises(IntegrityError):
        WishList.objects.create(user=wish_list_user)


def test_wish_list_item_unique_together(wish_list, wish_list_issue, wish_list_item):
    with pytest.raises(IntegrityError):
        WishListItem.objects.create(wish_list=wish_list, issue=wish_list_issue, priority=1)


def test_wish_list_item_signal_updates_modified(wish_list, wish_list_issue):
    original_modified = WishList.objects.get(pk=wish_list.pk).modified
    WishListItem.objects.create(wish_list=wish_list, issue=wish_list_issue, priority=1)
    updated_modified = WishList.objects.get(pk=wish_list.pk).modified
    assert updated_modified >= original_modified


def test_wish_list_item_delete_signal_updates_modified(wish_list, wish_list_item):
    original_modified = WishList.objects.get(pk=wish_list.pk).modified
    wish_list_item.delete()
    updated_modified = WishList.objects.get(pk=wish_list.pk).modified
    assert updated_modified >= original_modified


def test_wish_list_get_absolute_url(wish_list):
    url = wish_list.get_absolute_url()
    assert "/wish-list/" in url


def test_wish_list_item_status_default(wish_list, wish_list_issue):
    item = WishListItem.objects.create(wish_list=wish_list, issue=wish_list_issue)
    assert item.status == WishListItem.Status.WANTED


def test_wish_list_item_priority_default(wish_list, wish_list_issue):
    item = WishListItem.objects.create(wish_list=wish_list, issue=wish_list_issue)
    assert item.priority == 3


def test_wish_list_meta_ordering_is_set():
    assert WishList._meta.ordering
