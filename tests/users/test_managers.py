"""Tests for users.managers.OnePerUserManager (WishList / PullList ``for_user``)."""

import pytest

from pull_list.models import PullList
from wish_list.models import WishList


@pytest.mark.parametrize("model", [WishList, PullList])
def test_for_user_creates_then_returns_same_row(create_user, model):
    user = create_user()

    first = model.objects.for_user(user)
    second = model.objects.for_user(user)

    assert first.pk == second.pk
    assert model.objects.filter(user=user).count() == 1


@pytest.mark.parametrize("model", [WishList, PullList])
def test_for_user_reuses_the_user_object(create_user, model, django_assert_num_queries):
    user = create_user()
    obj = model.objects.for_user(user)

    with django_assert_num_queries(0):
        assert obj.user is user


@pytest.mark.parametrize("model", [WishList, PullList])
def test_for_user_rows_are_per_user(create_user, model):
    a, b = create_user(), create_user()
    assert model.objects.for_user(a).pk != model.objects.for_user(b).pk
