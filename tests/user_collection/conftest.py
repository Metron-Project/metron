"""Fixtures for user_collection app tests."""

from datetime import date

import pytest
from djmoney.money import Money

from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
from user_collection.models import CollectionItem


@pytest.fixture
def collection_user(db, create_user):
    """Create a user for collection tests."""
    return create_user(username="collection_user")


@pytest.fixture
def other_collection_user(db, create_user):
    """Create another user for permission tests."""
    return create_user(username="other_collection_user")


@pytest.fixture
def collection_publisher(create_user):
    """Create a publisher for collection tests."""
    user = create_user()
    return Publisher.objects.create(
        name="Collection Publisher", slug="collection-publisher", edited_by=user, created_by=user
    )


@pytest.fixture
def collection_series(create_user, collection_publisher, single_issue_type):
    """Create a series for collection tests."""
    user = create_user()
    return Series.objects.create(
        name="Collection Series",
        slug="collection-series",
        publisher=collection_publisher,
        volume="1",
        year_began=2023,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def collection_issue_1(create_user, collection_series):
    """Create the first issue for collection tests."""
    user = create_user()
    return Issue.objects.create(
        series=collection_series,
        number="1",
        slug="collection-series-1",
        cover_date=date(2023, 1, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def collection_issue_2(create_user, collection_series):
    """Create the second issue for collection tests."""
    user = create_user()
    return Issue.objects.create(
        series=collection_series,
        number="2",
        slug="collection-series-2",
        cover_date=date(2023, 2, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def collection_item(collection_user, collection_issue_1):
    """Create a basic collection item."""
    return CollectionItem.objects.create(
        user=collection_user,
        issue=collection_issue_1,
        quantity=1,
        book_format=CollectionItem.BookFormat.PRINT,
    )


@pytest.fixture
def collection_item_with_details(collection_user, collection_issue_2):
    """Create a collection item with all fields populated."""
    return CollectionItem.objects.create(
        user=collection_user,
        issue=collection_issue_2,
        quantity=2,
        book_format=CollectionItem.BookFormat.BOTH,
        purchase_date=date(2023, 6, 15),
        purchase_price=Money(4.99, "USD"),
        purchase_store="Local Comic Shop",
        storage_location="Long Box 3",
        notes="First printing, signed by artist",
    )
