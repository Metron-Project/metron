"""Fixtures for pull_list app tests."""

from datetime import date

import pytest

from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
from pull_list.models import PullList, PullListSeries


@pytest.fixture
def pull_list_user(db, create_user):
    return create_user(username="pull_list_user")


@pytest.fixture
def other_pull_list_user(db, create_user):
    return create_user(username="other_pull_list_user")


@pytest.fixture
def pull_list_publisher(create_user):
    user = create_user()
    return Publisher.objects.create(
        name="Pull List Publisher",
        slug="pull-list-publisher",
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def pull_list_series(create_user, pull_list_publisher, single_issue_type):
    user = create_user()
    return Series.objects.create(
        name="Pull List Series",
        slug="pull-list-series",
        publisher=pull_list_publisher,
        volume="1",
        year_began=2023,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def pull_list_series_2(create_user, pull_list_publisher, single_issue_type):
    user = create_user()
    return Series.objects.create(
        name="Another Pull List Series",
        slug="another-pull-list-series",
        publisher=pull_list_publisher,
        volume="1",
        year_began=2024,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def pull_list_issue(create_user, pull_list_series):
    user = create_user()
    return Issue.objects.create(
        series=pull_list_series,
        number="1",
        slug="pull-list-series-1",
        cover_date=date(2025, 6, 1),
        store_date=date(2025, 6, 4),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def public_pull_list(pull_list_user):
    return PullList.objects.create(user=pull_list_user, is_private=False)


@pytest.fixture
def private_pull_list(pull_list_user):
    return PullList.objects.create(user=pull_list_user, is_private=True)


@pytest.fixture
def pull_list_with_series(public_pull_list, pull_list_series):
    PullListSeries.objects.create(pull_list=public_pull_list, series=pull_list_series)
    return public_pull_list
