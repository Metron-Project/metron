"""Fixtures for reading_lists app tests."""

from datetime import date

import pytest

from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
from reading_lists.models import ReadingList, ReadingListItem


@pytest.fixture
def reading_list_user(db, create_user):
    """Create a user for reading list tests."""
    return create_user(username="readinglist_user")


@pytest.fixture
def other_user(db, create_user):
    """Create another user for permission tests."""
    return create_user(username="other_user")


@pytest.fixture
def reading_list_publisher(create_user):
    """Create a publisher for reading list tests."""
    user = create_user()
    return Publisher.objects.create(
        name="Test Publisher", slug="test-publisher", edited_by=user, created_by=user
    )


@pytest.fixture
def reading_list_series(create_user, reading_list_publisher, single_issue_type):
    """Create a series for reading list tests."""
    user = create_user()
    return Series.objects.create(
        name="Test Series",
        slug="test-series",
        publisher=reading_list_publisher,
        volume="1",
        year_began=2020,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def reading_list_issue_1(create_user, reading_list_series):
    """Create the first issue for reading list tests."""
    user = create_user()
    return Issue.objects.create(
        series=reading_list_series,
        number="1",
        slug="test-series-1",
        cover_date=date(2020, 1, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def reading_list_issue_2(create_user, reading_list_series):
    """Create the second issue for reading list tests."""
    user = create_user()
    return Issue.objects.create(
        series=reading_list_series,
        number="2",
        slug="test-series-2",
        cover_date=date(2020, 2, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def reading_list_issue_3(create_user, reading_list_series):
    """Create the third issue for reading list tests."""
    user = create_user()
    return Issue.objects.create(
        series=reading_list_series,
        number="3",
        slug="test-series-3",
        cover_date=date(2020, 3, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def public_reading_list(reading_list_user):
    """Create a public reading list."""
    return ReadingList.objects.create(
        user=reading_list_user,
        name="Public Reading List",
        desc="A public reading list for testing",
        is_private=False,
    )


@pytest.fixture
def private_reading_list(reading_list_user):
    """Create a private reading list."""
    return ReadingList.objects.create(
        user=reading_list_user,
        name="Private Reading List",
        desc="A private reading list for testing",
        is_private=True,
    )


@pytest.fixture
def reading_list_with_issues(
    reading_list_user,
    reading_list_issue_1,
    reading_list_issue_2,
    reading_list_issue_3,
):
    """Create a reading list with multiple issues."""
    reading_list = ReadingList.objects.create(
        user=reading_list_user,
        name="List With Issues",
        desc="A reading list with multiple issues",
        is_private=False,
        attribution_source=ReadingList.AttributionSource.CBRO,
        attribution_url="https://example.com/reading-order",
    )
    # Add issues in order
    ReadingListItem.objects.create(
        reading_list=reading_list,
        issue=reading_list_issue_1,
        order=1,
    )
    ReadingListItem.objects.create(
        reading_list=reading_list,
        issue=reading_list_issue_2,
        order=2,
    )
    ReadingListItem.objects.create(
        reading_list=reading_list,
        issue=reading_list_issue_3,
        order=3,
    )
    return reading_list


@pytest.fixture
def other_user_reading_list(other_user):
    """Create a reading list owned by another user."""
    return ReadingList.objects.create(
        user=other_user,
        name="Other User's List",
        desc="A reading list owned by another user",
        is_private=False,
    )


@pytest.fixture
def reading_list_item(reading_list_with_issues, reading_list_issue_1):
    """Get the first reading list item."""
    return ReadingListItem.objects.get(
        reading_list=reading_list_with_issues,
        issue=reading_list_issue_1,
    )


@pytest.fixture
def metron_user(db, create_user):
    """Create the Metron user for CBL imports."""
    return create_user(username="Metron")


@pytest.fixture
def admin_user(db, create_staff_user):
    """Create an admin user for permission tests."""
    return create_staff_user


@pytest.fixture
def metron_reading_list(metron_user):
    """Create a reading list owned by the Metron user."""
    return ReadingList.objects.create(
        user=metron_user,
        name="Metron's Reading List",
        desc="A reading list owned by Metron",
        is_private=False,
        attribution_source=ReadingList.AttributionSource.CBRO,
    )


@pytest.fixture
def metron_private_reading_list(metron_user):
    """Create a private reading list owned by the Metron user."""
    return ReadingList.objects.create(
        user=metron_user,
        name="Metron's Private List",
        desc="A private reading list owned by Metron",
        is_private=True,
    )


@pytest.fixture
def metron_reading_list_with_issues(
    metron_user,
    reading_list_issue_1,
    reading_list_issue_2,
    reading_list_issue_3,
):
    """Create a reading list with issues owned by Metron."""
    reading_list = ReadingList.objects.create(
        user=metron_user,
        name="Metron's List With Issues",
        desc="A reading list with multiple issues owned by Metron",
        is_private=False,
    )
    # Add issues in order
    ReadingListItem.objects.create(
        reading_list=reading_list,
        issue=reading_list_issue_1,
        order=1,
    )
    ReadingListItem.objects.create(
        reading_list=reading_list,
        issue=reading_list_issue_2,
        order=2,
    )
    ReadingListItem.objects.create(
        reading_list=reading_list,
        issue=reading_list_issue_3,
        order=3,
    )
    return reading_list
