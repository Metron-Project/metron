"""Tests for vendored django_nyt models."""

import pytest
from django.core.exceptions import ValidationError

from django_nyt import models as nyt_models
from django_nyt.models import (
    Notification,
    NotificationType,
    Settings,
    _glob_matches_path,
)

pytestmark = pytest.mark.django_db


class TestGlobMatchesPath:
    def test_exact_match(self):
        assert _glob_matches_path("admin/user", "admin/user") is True

    def test_single_star_matches_within_segment(self):
        assert _glob_matches_path("admin/*", "admin/user") is True

    def test_single_star_does_not_cross_slash(self):
        assert _glob_matches_path("admin/*", "admin/user/new") is False

    def test_double_star_crosses_slash(self):
        assert _glob_matches_path("admin/**", "admin/user/new") is True

    def test_no_match(self):
        assert _glob_matches_path("wiki/*", "admin/user") is False

    def test_question_mark_matches_single_char(self):
        assert _glob_matches_path("ab?", "abc") is True

    def test_question_mark_does_not_cross_slash(self):
        assert _glob_matches_path("ab?cd", "ab/cd") is False


class TestNotificationType:
    def test_get_by_key_creates_on_miss(self, db):
        nt = NotificationType.get_by_key("new/key")
        assert nt.pk == "new/key"
        assert NotificationType.objects.filter(key="new/key").exists()

    def test_get_by_key_returns_existing(self, notification_type):
        result = NotificationType.get_by_key(notification_type.key)
        assert result.pk == notification_type.pk

    def test_get_by_key_caches_result(self, notification_type):
        NotificationType.get_by_key(notification_type.key)
        assert notification_type.key in nyt_models._notification_type_cache
        second = NotificationType.get_by_key(notification_type.key)
        assert second is nyt_models._notification_type_cache[notification_type.key]

    def test_delete_clears_cache(self, notification_type):
        NotificationType.get_by_key(notification_type.key)
        notification_type.delete()
        assert notification_type.key not in nyt_models._notification_type_cache

    def test_str_returns_key(self, notification_type):
        assert str(notification_type) == notification_type.key


class TestSettings:
    def test_get_default_settings_creates_if_missing(self, db, create_user):
        user = create_user()
        settings = Settings.get_default_settings(user)
        assert settings.is_default is True
        assert settings.user == user

    def test_get_default_settings_returns_existing(self, nyt_settings, nyt_user):
        result = Settings.get_default_settings(nyt_user)
        assert result.pk == nyt_settings.pk

    def test_new_default_clears_old_default(self, nyt_settings, nyt_user):
        new_settings = Settings.objects.create(user=nyt_user, is_default=True)
        nyt_settings.refresh_from_db()
        assert new_settings.is_default is True
        assert nyt_settings.is_default is False

    def test_clean_raises_if_only_default_unset(self, nyt_settings):
        nyt_settings.is_default = False
        with pytest.raises(ValidationError):
            nyt_settings.clean()

    def test_str_contains_username(self, nyt_settings, nyt_user):
        assert nyt_user.username in str(nyt_settings)


class TestNotificationCreateNotifications:
    def test_creates_notification_for_subscriber(self, subscription, nyt_user):
        notifications = Notification.create_notifications(
            "test/event", message="Hello", url="/test/"
        )
        assert len(notifications) == 1
        assert notifications[0].message == "Hello"
        assert notifications[0].user == nyt_user

    def test_increments_occurrences_for_duplicate(self, subscription):
        Notification.create_notifications("test/event", message="Hello", url="/test/")
        Notification.create_notifications("test/event", message="Hello", url="/test/")
        assert Notification.objects.count() == 1
        assert Notification.objects.first().occurrences == 2

    def test_creates_new_notification_when_message_differs(self, subscription):
        Notification.create_notifications("test/event", message="First", url="/test/")
        Notification.create_notifications("test/event", message="Second", url="/test/")
        assert Notification.objects.count() == 2

    def test_creates_new_notification_when_already_viewed(self, subscription):
        notifications = Notification.create_notifications(
            "test/event", message="Hello", url="/test/"
        )
        notifications[0].is_viewed = True
        notifications[0].save()
        Notification.create_notifications("test/event", message="Hello", url="/test/")
        assert Notification.objects.count() == 2

    def test_raises_for_empty_key(self, db):
        with pytest.raises(KeyError):
            Notification.create_notifications("", message="Hello")

    def test_returns_empty_list_when_no_subscribers(self, db):
        result = Notification.create_notifications("no/subscribers", message="Hello")
        assert result == []

    def test_recipient_users_filter_excludes_non_matching(
        self, subscription, create_user
    ):
        other_user = create_user()
        notifications = Notification.create_notifications(
            "test/event", message="Hello", recipient_users=[other_user]
        )
        assert notifications == []
