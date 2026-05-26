"""Tests for vendored django_nyt views."""

import pytest

from django_nyt.models import Notification

pytestmark = pytest.mark.django_db

NYT_PREFIX = "/notifications"


class TestGetNotifications:
    def test_unauthenticated_ajax_returns_403(self, client):
        response = client.get(
            f"{NYT_PREFIX}/json/get/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.status_code == 403

    def test_unauthenticated_non_ajax_redirects_to_login(self, client):
        response = client.get(f"{NYT_PREFIX}/json/get/")
        assert response.status_code == 302

    def test_returns_empty_for_user_with_no_notifications(self, auto_login_user):
        client, _user = auto_login_user()
        response = client.get(
            f"{NYT_PREFIX}/json/get/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["objects"] == []
        assert data["total_count"] == 0

    def test_returns_unread_notifications(self, auto_login_user, subscription):
        client, user = auto_login_user(user=subscription.settings.user)
        Notification.objects.create(
            subscription=subscription, user=user, message="Test notification"
        )
        response = client.get(
            f"{NYT_PREFIX}/json/get/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        data = response.json()
        assert data["total_count"] == 1
        assert data["objects"][0]["message"] == "Test notification"

    def test_latest_id_filters_older_notifications(self, auto_login_user, subscription):
        client, user = auto_login_user(user=subscription.settings.user)
        n1 = Notification.objects.create(
            subscription=subscription, user=user, message="Old"
        )
        Notification.objects.create(
            subscription=subscription, user=user, message="New"
        )
        response = client.get(
            f"{NYT_PREFIX}/json/get/{n1.pk}/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        data = response.json()
        assert len(data["objects"]) == 1
        assert data["objects"][0]["message"] == "New"

    def test_does_not_return_other_users_notifications(
        self, auto_login_user, subscription, create_user
    ):
        other_user = create_user()
        Notification.objects.create(
            subscription=subscription,
            user=subscription.settings.user,
            message="Not yours",
        )
        client, _user = auto_login_user(user=other_user)
        response = client.get(
            f"{NYT_PREFIX}/json/get/", HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        assert response.json()["total_count"] == 0


class TestGoto:
    def test_redirects_to_notification_url_and_marks_viewed(
        self, auto_login_user, subscription
    ):
        client, user = auto_login_user(user=subscription.settings.user)
        notification = Notification.objects.create(
            subscription=subscription, user=user, message="Go here", url="/some/path/"
        )
        response = client.get(f"{NYT_PREFIX}/goto/{notification.pk}/")
        assert response.status_code == 302
        assert response["Location"] == "/some/path/"
        notification.refresh_from_db()
        assert notification.is_viewed is True

    def test_redirects_to_referer_when_notification_has_no_url(
        self, auto_login_user, subscription
    ):
        client, user = auto_login_user(user=subscription.settings.user)
        notification = Notification.objects.create(
            subscription=subscription, user=user, message="No URL"
        )
        response = client.get(
            f"{NYT_PREFIX}/goto/{notification.pk}/", HTTP_REFERER="/previous/"
        )
        assert response.status_code == 302
        assert response["Location"] == "/previous/"

    def test_returns_404_for_another_users_notification(
        self, auto_login_user, subscription, create_user
    ):
        other_user = create_user()
        notification = Notification.objects.create(
            subscription=subscription,
            user=subscription.settings.user,
            message="Not yours",
            url="/test/",
        )
        client, _user = auto_login_user(user=other_user)
        response = client.get(f"{NYT_PREFIX}/goto/{notification.pk}/")
        assert response.status_code == 404

    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get(f"{NYT_PREFIX}/goto/1/")
        assert response.status_code == 302


class TestMarkRead:
    def test_marks_notifications_at_or_below_id_as_viewed(
        self, auto_login_user, subscription
    ):
        client, user = auto_login_user(user=subscription.settings.user)
        n1 = Notification.objects.create(
            subscription=subscription, user=user, message="A"
        )
        n2 = Notification.objects.create(
            subscription=subscription, user=user, message="B"
        )
        response = client.get(
            f"{NYT_PREFIX}/json/mark-read/{n2.pk}/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        n1.refresh_from_db()
        n2.refresh_from_db()
        assert n1.is_viewed is True
        assert n2.is_viewed is True

    def test_does_not_mark_notifications_above_id(
        self, auto_login_user, subscription
    ):
        client, user = auto_login_user(user=subscription.settings.user)
        n1 = Notification.objects.create(
            subscription=subscription, user=user, message="A"
        )
        n2 = Notification.objects.create(
            subscription=subscription, user=user, message="B"
        )
        client.get(
            f"{NYT_PREFIX}/json/mark-read/{n1.pk}/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        n2.refresh_from_db()
        assert n2.is_viewed is False

    def test_unauthenticated_ajax_returns_403(self, client):
        response = client.get(
            f"{NYT_PREFIX}/json/mark-read/999/",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        assert response.status_code == 403
