"""Tests for wish_list models."""

import pytest
from django.db import IntegrityError

from wish_list.models import WishList, WishListItem


def test_wish_list_str(public_wish_list, wish_list_user):
    assert str(public_wish_list) == f"{wish_list_user.username}'s Wish List"


def test_wish_list_item_str(wish_list_item, wish_list_user):
    s = str(wish_list_item)
    assert wish_list_user.username in s
    assert "Wanted" in s


def test_wish_list_one_per_user(wish_list_user, public_wish_list):
    with pytest.raises(IntegrityError):
        WishList.objects.create(user=wish_list_user)


def test_wish_list_item_unique_together(public_wish_list, wish_list_issue, wish_list_item):
    with pytest.raises(IntegrityError):
        WishListItem.objects.create(wish_list=public_wish_list, issue=wish_list_issue, priority=1)


def test_wish_list_item_signal_updates_modified(public_wish_list, wish_list_issue):
    original_modified = WishList.objects.get(pk=public_wish_list.pk).modified
    WishListItem.objects.create(wish_list=public_wish_list, issue=wish_list_issue, priority=1)
    updated_modified = WishList.objects.get(pk=public_wish_list.pk).modified
    assert updated_modified >= original_modified


def test_wish_list_item_delete_signal_updates_modified(public_wish_list, wish_list_item):
    original_modified = WishList.objects.get(pk=public_wish_list.pk).modified
    wish_list_item.delete()
    updated_modified = WishList.objects.get(pk=public_wish_list.pk).modified
    assert updated_modified >= original_modified


def test_wish_list_get_absolute_url(public_wish_list):
    url = public_wish_list.get_absolute_url()
    assert "/wish-list/" in url


def test_wish_list_item_status_default(public_wish_list, wish_list_issue):
    item = WishListItem.objects.create(wish_list=public_wish_list, issue=wish_list_issue)
    assert item.status == WishListItem.Status.WANTED


def test_wish_list_item_priority_default(public_wish_list, wish_list_issue):
    item = WishListItem.objects.create(wish_list=public_wish_list, issue=wish_list_issue)
    assert item.priority == 3
