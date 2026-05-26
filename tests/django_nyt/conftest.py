"""Fixtures for django_nyt tests."""

import pytest

from django_nyt import models


@pytest.fixture(autouse=True)
def clear_notification_type_cache():
    yield
    models._notification_type_cache = {}


@pytest.fixture
def nyt_user(create_user):
    return create_user()


@pytest.fixture
def nyt_settings(db, nyt_user):
    return models.Settings.objects.create(user=nyt_user, is_default=True)


@pytest.fixture
def notification_type(db):
    return models.NotificationType.objects.create(key="test/event")


@pytest.fixture
def subscription(nyt_settings, notification_type):
    return models.Subscription.objects.create(
        settings=nyt_settings,
        notification_type=notification_type,
    )
