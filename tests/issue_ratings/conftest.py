"""Fixtures for issue_ratings app tests."""

from datetime import date

import pytest

from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series


@pytest.fixture
def rating_user(db, create_user):
    """Create a user for issue rating tests."""
    return create_user(username="rating_user")


@pytest.fixture
def other_rating_user(db, create_user):
    """Create another user for issue rating tests."""
    return create_user(username="other_rating_user")


@pytest.fixture
def rating_publisher(create_user):
    """Create a publisher for issue rating tests."""
    user = create_user()
    return Publisher.objects.create(
        name="Rating Test Publisher", slug="rating-test-publisher", edited_by=user, created_by=user
    )


@pytest.fixture
def rating_series(create_user, rating_publisher, single_issue_type):
    """Create a series for issue rating tests."""
    user = create_user()
    return Series.objects.create(
        name="Rating Test Series",
        slug="rating-test-series",
        publisher=rating_publisher,
        volume="1",
        year_began=2020,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def rating_issue(create_user, rating_series):
    """Create an issue for issue rating tests."""
    user = create_user()
    return Issue.objects.create(
        series=rating_series,
        number="1",
        slug="rating-test-series-1",
        cover_date=date(2020, 1, 1),
        edited_by=user,
        created_by=user,
    )
