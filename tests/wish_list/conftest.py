"""Fixtures for wish_list app tests."""

from datetime import date

import pytest

from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
from wish_list.models import WishList, WishListItem


@pytest.fixture
def wish_list_user(db, create_user):
    return create_user(username="wish_list_user")


@pytest.fixture
def other_wish_list_user(db, create_user):
    return create_user(username="other_wish_list_user")


@pytest.fixture
def wish_list_publisher(create_user):
    user = create_user()
    return Publisher.objects.create(
        name="Wish List Publisher",
        slug="wish-list-publisher",
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def wish_list_series(create_user, wish_list_publisher, single_issue_type):
    user = create_user()
    return Series.objects.create(
        name="Wish List Series",
        slug="wish-list-series",
        publisher=wish_list_publisher,
        volume="1",
        year_began=2020,
        series_type=single_issue_type,
        status=Series.Status.COMPLETED,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def wish_list_issue(create_user, wish_list_series):
    user = create_user()
    return Issue.objects.create(
        series=wish_list_series,
        number="1",
        slug="wish-list-series-1",
        cover_date=date(2020, 1, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def wish_list_issue_2(create_user, wish_list_series):
    user = create_user()
    return Issue.objects.create(
        series=wish_list_series,
        number="2",
        slug="wish-list-series-2",
        cover_date=date(2020, 2, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def public_wish_list(wish_list_user):
    return WishList.objects.create(user=wish_list_user, is_private=False)


@pytest.fixture
def private_wish_list(wish_list_user):
    return WishList.objects.create(user=wish_list_user, is_private=True)


@pytest.fixture
def wish_list_item(public_wish_list, wish_list_issue):
    return WishListItem.objects.create(
        wish_list=public_wish_list,
        issue=wish_list_issue,
        priority=1,
        status=WishListItem.Status.WANTED,
    )


@pytest.fixture
def wish_list_item_2(public_wish_list, wish_list_issue_2):
    return WishListItem.objects.create(
        wish_list=public_wish_list,
        issue=wish_list_issue_2,
        priority=2,
        status=WishListItem.Status.WANTED,
    )
