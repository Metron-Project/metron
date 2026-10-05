"""Tests for the password-gated, confirm-by-link email change flow."""

import re
import smtplib
from unittest.mock import patch
from urllib.parse import urlsplit

import pytest
from django.core import mail, signing
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from users.models import CustomUser
from users.views import EMAIL_CHANGE_SALT

HTML_OK_CODE = 200
HTTP_REDIRECT_FOUND_CODE = 302
NEW_EMAIL = "new-address@gmail.com"  # Allowlisted domain: skips the RapidAPI check.


def _profile_data(user, **overrides):
    return {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "bio": "",
        **overrides,
    }


def _confirm_url_from(message):
    match = re.search(r"https?://\S+/accounts/email/confirm/\S+/", message.body)
    assert match, message.body
    return urlsplit(match.group(0)).path


@pytest.fixture
def requested_change(auto_login_user, test_password):
    """A logged-in user who has requested a change to NEW_EMAIL."""
    client, user = auto_login_user()
    resp = client.post(
        reverse("change_profile"),
        _profile_data(user, email=NEW_EMAIL, current_password=test_password),
    )
    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    return client, user


class TestEmailChangeRequest:
    def test_other_fields_change_without_password(self, auto_login_user):
        client, user = auto_login_user()
        resp = client.post(reverse("change_profile"), _profile_data(user, first_name="Walt"))
        assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
        user.refresh_from_db()
        assert user.first_name == "Walt"
        assert mail.outbox == []

    @pytest.mark.parametrize("password", ["", "wrong-password"])
    def test_email_change_requires_correct_password(self, auto_login_user, password):
        client, user = auto_login_user()
        old_email = user.email
        resp = client.post(
            reverse("change_profile"),
            _profile_data(user, email=NEW_EMAIL, current_password=password),
        )
        assert resp.status_code == HTML_OK_CODE
        assert resp.context["form"].errors["current_password"]
        user.refresh_from_db()
        assert user.email == old_email
        assert mail.outbox == []

    def test_email_unchanged_until_confirmed(self, requested_change, test_email):
        _client, user = requested_change
        user.refresh_from_db()
        assert user.email == test_email

    def test_sends_confirmation_to_new_and_notice_to_old(self, requested_change, test_email):
        confirm, notice = mail.outbox
        assert confirm.to == [NEW_EMAIL]
        assert "/accounts/email/confirm/" in confirm.body
        assert notice.to == [test_email]
        assert NEW_EMAIL in notice.body
        assert "/accounts/email/confirm/" not in notice.body

    def test_emails_include_html_versions(self, requested_change):
        for message in mail.outbox:
            ((html, mimetype),) = message.alternatives
            assert mimetype == "text/html"
            assert "<html" in html
        assert "/accounts/email/confirm/" in mail.outbox[0].alternatives[0][0]
        assert "/accounts/password_reset/" in mail.outbox[1].alternatives[0][0]

    def test_links_use_https_on_secure_requests(self, auto_login_user, test_password):
        client, user = auto_login_user()
        client.post(
            reverse("change_profile"),
            _profile_data(user, email=NEW_EMAIL, current_password=test_password),
            secure=True,
        )
        confirm, notice = mail.outbox
        assert "https://" in confirm.body
        assert "http://" not in confirm.body
        assert "https://" in notice.alternatives[0][0]

    def test_html_notice_escapes_new_address(self, auto_login_user, test_password):
        """A quoted local part may legally contain markup; it must not render as HTML."""
        hostile = '"<b>x</b>"@gmail.com'
        client, user = auto_login_user()
        client.post(
            reverse("change_profile"),
            _profile_data(user, email=hostile, current_password=test_password),
        )
        _confirm, notice = mail.outbox
        html = notice.alternatives[0][0]
        assert "<b>x</b>" not in html
        assert "&lt;b&gt;x&lt;/b&gt;" in html

    def test_rejects_address_used_by_another_account(self, auto_login_user, test_password):
        CustomUser.objects.create_user(username="taken", email="Taken@Gmail.com")
        client, user = auto_login_user()
        resp = client.post(
            reverse("change_profile"),
            _profile_data(user, email="taken@gmail.com", current_password=test_password),
        )
        assert resp.status_code == HTML_OK_CODE
        assert resp.context["form"].errors["email"]
        assert mail.outbox == []

    def test_rejects_disposable_address(self, auto_login_user, test_password):
        client, user = auto_login_user()
        resp = client.post(
            reverse("change_profile"),
            _profile_data(user, email="someone@duck.com", current_password=test_password),
        )
        assert resp.status_code == HTML_OK_CODE
        assert resp.context["form"].errors["email"]

    def test_runs_domain_check_for_unlisted_domains(self, auto_login_user, test_password):
        client, user = auto_login_user()
        blocked = {"block": True, "disposable": True}
        with patch("users.forms.check_email_domain", return_value=blocked) as mock_check:
            resp = client.post(
                reverse("change_profile"),
                _profile_data(user, email="x@example.org", current_password=test_password),
            )
        mock_check.assert_called_once_with("x@example.org")
        assert resp.context["form"].errors["email"]

    def test_send_failure_saves_nothing(self, auto_login_user, test_password, test_email):
        client, user = auto_login_user()
        with patch(
            "users.views.EmailMultiAlternatives.send",
            side_effect=smtplib.SMTPException("down"),
        ):
            resp = client.post(
                reverse("change_profile"),
                _profile_data(
                    user, email=NEW_EMAIL, first_name="Walt", current_password=test_password
                ),
            )
        assert resp.status_code == HTML_OK_CODE
        assertTemplateUsed(resp, "users/change_profile.html")
        assert resp.context["form"].errors["email"]
        user.refresh_from_db()
        assert user.email == test_email
        assert user.first_name != "Walt"


class TestEmailChangeConfirmation:
    def test_link_applies_change(self, requested_change):
        client, user = requested_change
        user.email_confirmed = False
        user.save(update_fields=["email_confirmed"])

        resp = client.get(_confirm_url_from(mail.outbox[0]))
        assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
        assert resp.url == reverse("user-detail", kwargs={"username": user.username})
        user.refresh_from_db()
        assert user.email == NEW_EMAIL
        assert user.email_confirmed is True

    def test_link_works_without_being_logged_in(self, requested_change, client):
        _client, user = requested_change
        client.logout()
        resp = client.get(_confirm_url_from(mail.outbox[0]))
        assert resp.url == reverse("login")
        user.refresh_from_db()
        assert user.email == NEW_EMAIL

    def test_link_cannot_be_reused(self, requested_change):
        client, user = requested_change
        url = _confirm_url_from(mail.outbox[0])
        client.get(url)
        user.refresh_from_db()
        assert user.email == NEW_EMAIL

        resp = client.get(url, follow=True)
        assert "invalid or has expired" in resp.content.decode()

    def test_expired_link_rejected(self, requested_change, test_email):
        client, user = requested_change
        with patch("users.views.EMAIL_CHANGE_MAX_AGE", -1):
            resp = client.get(_confirm_url_from(mail.outbox[0]))
        assert resp.url == reverse("home")
        user.refresh_from_db()
        assert user.email == test_email

    def test_tampered_link_rejected(self, auto_login_user, test_email):
        client, user = auto_login_user()
        token = signing.dumps(
            {"user": user.pk, "old_email": test_email, "new_email": NEW_EMAIL},
            salt="some-other-salt",
        )
        client.get(reverse("confirm_email_change", kwargs={"token": token}))
        user.refresh_from_db()
        assert user.email == test_email

    def test_address_taken_before_confirmation(self, requested_change, test_email):
        client, user = requested_change
        CustomUser.objects.create_user(username="taken", email=NEW_EMAIL)
        resp = client.get(_confirm_url_from(mail.outbox[0]))
        assert resp.url == reverse("home")
        user.refresh_from_db()
        assert user.email == test_email

    def test_token_uses_email_change_salt(self, requested_change, test_email):
        _client, user = requested_change
        token = _confirm_url_from(mail.outbox[0]).rstrip("/").rsplit("/", 1)[1]
        data = signing.loads(token, salt=EMAIL_CHANGE_SALT)
        assert data == {"user": user.pk, "old_email": test_email, "new_email": NEW_EMAIL}
