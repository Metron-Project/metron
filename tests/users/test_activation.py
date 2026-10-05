"""Tests for account activation links."""

from urllib.parse import quote

import pytest
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from pytest_django.asserts import assertTemplateUsed

from users.tokens import account_activation_token

HTML_OK_CODE = 200
HTTP_REDIRECT_FOUND_CODE = 302


@pytest.fixture
def inactive_user(create_user):
    user = create_user()
    user.is_active = False
    user.email_confirmed = False
    user.save(update_fields=["is_active", "email_confirmed"])
    return user


def _uid_and_token(user):
    return urlsafe_base64_encode(force_bytes(user.pk)), account_activation_token.make_token(user)


def _legacy_path(uidb64, token):
    """The link format sent while the activate route was a regex passed to path()."""
    raw = (
        f"/accounts/activate/(?{uidb64}[0-9A-Za-z_\\-]+)/"
        f"(?{token}[0-9A-Za-z]{{1,13}}-[0-9A-Za-z]{{1,20}})/"
    )
    # reverse() percent-encoded the regex characters (e.g. "?" as %3F) in emailed links.
    return quote(raw)


def test_activate_url_is_clean(inactive_user):
    uidb64, token = _uid_and_token(inactive_user)
    url = reverse("activate", kwargs={"uidb64": uidb64, "token": token})
    assert url == f"/accounts/activate/{uidb64}/{token}/"


def test_valid_link_activates_and_logs_in(client, inactive_user):
    uidb64, token = _uid_and_token(inactive_user)
    resp = client.get(reverse("activate", kwargs={"uidb64": uidb64, "token": token}))

    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert resp.url == reverse("home")
    inactive_user.refresh_from_db()
    assert inactive_user.is_active is True
    assert inactive_user.email_confirmed is True
    assert int(client.session["_auth_user_id"]) == inactive_user.pk


def test_link_cannot_be_reused(client, inactive_user):
    uidb64, token = _uid_and_token(inactive_user)
    url = reverse("activate", kwargs={"uidb64": uidb64, "token": token})
    client.get(url)
    client.logout()

    resp = client.get(url)
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "registration/account_activation_invalid.html")


@pytest.mark.parametrize(
    ("uidb64", "token"),
    [("bm90LWEtdXNlcg", "abc-123"), ("!!!", "abc-123")],
)
def test_invalid_link_rejected(client, inactive_user, uidb64, token):
    resp = client.get(f"/accounts/activate/{uidb64}/{token}/")
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "registration/account_activation_invalid.html")
    inactive_user.refresh_from_db()
    assert inactive_user.is_active is False


def test_wrong_token_rejected(client, inactive_user):
    uidb64, _token = _uid_and_token(inactive_user)
    resp = client.get(reverse("activate", kwargs={"uidb64": uidb64, "token": "abc-123"}))
    assertTemplateUsed(resp, "registration/account_activation_invalid.html")
    inactive_user.refresh_from_db()
    assert inactive_user.is_active is False


def test_legacy_link_still_activates(client, inactive_user):
    uidb64, token = _uid_and_token(inactive_user)
    resp = client.get(_legacy_path(uidb64, token))

    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    inactive_user.refresh_from_db()
    assert inactive_user.is_active is True
