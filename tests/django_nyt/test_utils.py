"""Tests for vendored django_nyt notify/subscribe/unsubscribe utilities."""

import pytest

import django_nyt
from django_nyt import utils
from django_nyt.models import Notification, NotificationType, Subscription

pytestmark = pytest.mark.django_db


class TestNotify:
    def test_creates_notification_for_subscriber(self, subscription, nyt_user):
        notifications = utils.notify("Test message", "test/event")
        assert len(notifications) == 1
        assert notifications[0].user == nyt_user
        assert notifications[0].message == "Test message"

    def test_returns_empty_list_when_notifications_disabled(self, subscription):
        django_nyt._disable_notifications = True
        try:
            result = utils.notify("Test message", "test/event")
        finally:
            django_nyt._disable_notifications = False
        assert result == []

    def test_raises_for_non_model_target_object(self, db):
        with pytest.raises(TypeError):
            utils.notify("Message", "test/event", target_object="not-a-model")

    def test_returns_empty_list_when_no_subscribers(self, db):
        result = utils.notify("Hello", "no/subscribers")
        assert result == []


class TestSubscribe:
    def test_creates_subscription(self, nyt_settings):
        sub = utils.subscribe(nyt_settings, "new/key")
        assert sub.notification_type.key == "new/key"
        assert Subscription.objects.filter(
            settings=nyt_settings, notification_type__key="new/key"
        ).exists()

    def test_is_idempotent(self, nyt_settings):
        utils.subscribe(nyt_settings, "new/key")
        utils.subscribe(nyt_settings, "new/key")
        assert (
            Subscription.objects.filter(
                settings=nyt_settings, notification_type__key="new/key"
            ).count()
            == 1
        )

    def test_creates_notification_type_if_missing(self, nyt_settings):
        utils.subscribe(nyt_settings, "brand/new/key")
        assert NotificationType.objects.filter(key="brand/new/key").exists()


class TestUnsubscribe:
    def test_unsubscribe_by_user(self, subscription, nyt_user):
        utils.unsubscribe("test/event", user=nyt_user)
        assert not Subscription.objects.filter(pk=subscription.pk).exists()

    def test_unsubscribe_by_settings(self, subscription, nyt_settings):
        utils.unsubscribe("test/event", settings=nyt_settings)
        assert not Subscription.objects.filter(pk=subscription.pk).exists()

    def test_raises_with_both_user_and_settings(
        self, subscription, nyt_user, nyt_settings
    ):
        with pytest.raises(AssertionError):
            utils.unsubscribe("test/event", user=nyt_user, settings=nyt_settings)

    def test_raises_with_neither_user_nor_settings(self, subscription):
        with pytest.raises(AssertionError):
            utils.unsubscribe("test/event")

    def test_only_removes_matching_subscription(self, nyt_settings, create_user):
        other_user = create_user()
        other_settings = utils.subscribe(
            nyt_settings.__class__.objects.create(user=other_user, is_default=True),
            "test/event",
        ).settings
        sub_to_keep = utils.subscribe(other_settings, "test/event")
        utils.unsubscribe("test/event", user=nyt_settings.user)
        assert Subscription.objects.filter(pk=sub_to_keep.pk).exists()

    def test_notification_objects_survive_unsubscribe(self, subscription, nyt_user):
        Notification.objects.create(
            subscription=subscription,
            user=nyt_user,
            message="Persisted",
        )
        utils.unsubscribe("test/event", user=nyt_user)
        assert Notification.objects.filter(message="Persisted").exists()
