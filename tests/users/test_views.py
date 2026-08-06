import time
import uuid
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from users.forms import CustomUserChangeForm
from users.models import ApiToken, CustomUser, SignupSettings
from users.views import SIGNUP_IP_LIMIT, SUSTAINED_DURATION, SUSTAINED_LIMIT, get_rate_limit_usage

HTTP_NOT_FOUND_CODE = 404

HTML_REDIRECT_MOVED_PERMAMENTLY_CODE = 301
HTTP_REDIRECT_FOUND_CODE = 302
HTML_OK_CODE = 200
HTTP_TOO_MANY_REQUESTS_CODE = 429


@pytest.mark.parametrize("url", ["/accounts/update/", "/accounts/password/", "/accounts/signup/"])
def test_view_url_exists_at_desired_location(auto_login_user, url):
    client, _ = auto_login_user()
    resp = client.get(url)
    assert resp.status_code == HTML_OK_CODE


# @pytest.mark.parametrize("url", ["/accounts/update", "/accounts/password", "/accounts/signup"])  # noqa: E501
# def test_view_url_exists_at_desired_location_redirected(auto_login_user, url):
#     client, _ = auto_login_user()
#     resp = client.get(url)
#     assert resp.status_code == HTML_REDIRECT_CODE


@pytest.mark.parametrize("url", ["change_profile", "change_password", "signup"])
def test_view_url_accessible_by_name(auto_login_user, url):
    client, _ = auto_login_user()
    resp = client.get(reverse(url))
    assert resp.status_code == HTML_OK_CODE


@pytest.mark.parametrize("url", ["change_profile", "change_password"])
def test_view_uses_correct_template(auto_login_user, url):
    client, _ = auto_login_user()
    resp = client.get(reverse(url))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, f"users/{url}.html")


@pytest.mark.parametrize("url", ["signup"])
def test_signup_view_uses_correct_template(auto_login_user, url):
    client, _ = auto_login_user()
    resp = client.get(reverse(url))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, f"registration/{url}.html")


def test_signup_settings_get_solo_creates_default(db):
    assert not SignupSettings.objects.exists()
    settings_obj = SignupSettings.get_solo()
    assert settings_obj.pk == 1
    assert settings_obj.signups_enabled is True


def test_signup_view_disabled_renders_disabled_template(db, client):
    SignupSettings.objects.create(pk=1, signups_enabled=False, disabled_message="No signups.")
    resp = client.get(reverse("signup"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "registration/signups_disabled.html")
    assert b"No signups." in resp.content


def test_signup_view_disabled_blocks_post(db, client):
    SignupSettings.objects.create(pk=1, signups_enabled=False)
    user_count_before = CustomUser.objects.count()
    resp = client.post(
        reverse("signup"),
        {
            "username": "newuser",
            "email": "newuser@example.com",
            "password1": "some-strong-password-1",
            "password2": "some-strong-password-1",
        },
    )
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "registration/signups_disabled.html")
    assert CustomUser.objects.count() == user_count_before


def _signup_payload(suffix):
    return {
        "username": f"newuser{suffix}",
        "email": f"newuser{suffix}@gmail.com",
        "password1": "some-strong-password-1",
        "password2": "some-strong-password-1",
    }


def _unique_ip():
    # Unique-per-call identity (rather than a fixed address or a narrow
    # 0-255 range) so repeated local runs against the real (shared) cache
    # backend, and other tests in the same run, can't collide on the same
    # rate-limit bucket - mirrors tests/api/test_client_health.py, but with
    # a wider ID space since SIGNUP_IP_LIMIT is small enough that even one
    # coincidental collision would trip the limit early.
    return f"203.0.113.{uuid.uuid4().hex}"


def test_signup_ip_rate_limit_allows_up_to_limit(db, client):
    ip = _unique_ip()
    user_count_before = CustomUser.objects.count()
    with (
        patch("users.views.get_recaptcha_auth", return_value={"success": True}),
        patch("users.views.send_pushover"),
    ):
        for i in range(SIGNUP_IP_LIMIT):
            resp = client.post(reverse("signup"), _signup_payload(i), REMOTE_ADDR=ip)
            assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert CustomUser.objects.count() == user_count_before + SIGNUP_IP_LIMIT


def test_signup_ip_rate_limit_blocks_after_limit(db, client):
    ip = _unique_ip()
    with (
        patch("users.views.get_recaptcha_auth", return_value={"success": True}),
        patch("users.views.send_pushover") as mock_pushover,
    ):
        for i in range(SIGNUP_IP_LIMIT):
            client.post(reverse("signup"), _signup_payload(i), REMOTE_ADDR=ip)
        user_count_before = CustomUser.objects.count()
        mock_pushover.reset_mock()

        resp = client.post(reverse("signup"), _signup_payload("extra"), REMOTE_ADDR=ip)

    assert resp.status_code == HTTP_TOO_MANY_REQUESTS_CODE
    assertTemplateUsed(resp, "registration/signup_rate_limited.html")
    assert CustomUser.objects.count() == user_count_before
    mock_pushover.assert_called_once()
    message = mock_pushover.call_args[0][0]
    assert ip in message
    assert "newuser0" in message  # username of the first signup from this IP


def test_signup_ip_rate_limit_notifies_once_per_ip_per_day(db, client):
    ip = _unique_ip()
    with (
        patch("users.views.get_recaptcha_auth", return_value={"success": True}),
        patch("users.views.send_pushover") as mock_pushover,
    ):
        for i in range(SIGNUP_IP_LIMIT):
            client.post(reverse("signup"), _signup_payload(i), REMOTE_ADDR=ip)
        mock_pushover.reset_mock()

        # Two blocked attempts in a row from the same IP should only notify once.
        client.post(reverse("signup"), _signup_payload("extra-1"), REMOTE_ADDR=ip)
        client.post(reverse("signup"), _signup_payload("extra-2"), REMOTE_ADDR=ip)

    mock_pushover.assert_called_once()


def test_signup_ip_rate_limit_is_per_ip(db, client):
    busy_ip = _unique_ip()
    other_ip = _unique_ip()
    with (
        patch("users.views.get_recaptcha_auth", return_value={"success": True}),
        patch("users.views.send_pushover"),
    ):
        for i in range(SIGNUP_IP_LIMIT):
            client.post(reverse("signup"), _signup_payload(i), REMOTE_ADDR=busy_ip)

        resp = client.post(reverse("signup"), _signup_payload("other-ip"), REMOTE_ADDR=other_ip)

    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE


def test_signup_ip_rate_limit_prefers_x_real_ip_over_remote_addr(db, client):
    # Simulates sitting behind nginx (nginx/nginx.conf), which sets X-Real-IP
    # to its own view of the connecting client and REMOTE_ADDR to nginx's own
    # address. Two requests presented with the same X-Real-IP but different
    # REMOTE_ADDR should share one rate-limit bucket.
    real_ip = _unique_ip()
    user_count_before = CustomUser.objects.count()
    with (
        patch("users.views.get_recaptcha_auth", return_value={"success": True}),
        patch("users.views.send_pushover"),
    ):
        for i in range(SIGNUP_IP_LIMIT):
            resp = client.post(
                reverse("signup"),
                _signup_payload(i),
                REMOTE_ADDR=_unique_ip(),
                HTTP_X_REAL_IP=real_ip,
            )
            assert resp.status_code == HTTP_REDIRECT_FOUND_CODE

        resp = client.post(
            reverse("signup"),
            _signup_payload("extra"),
            REMOTE_ADDR=_unique_ip(),
            HTTP_X_REAL_IP=real_ip,
        )

    assert resp.status_code == HTTP_TOO_MANY_REQUESTS_CODE
    assert CustomUser.objects.count() == user_count_before + SIGNUP_IP_LIMIT


def test_profile_view_url_exists_at_desired_location(auto_login_user):
    client, user = auto_login_user()
    resp = client.get(f"/accounts/{user.username}/")
    assert resp.status_code == HTML_OK_CODE


def test_profile_view_pk_redirects_to_username(auto_login_user):
    client, user = auto_login_user()
    resp = client.get(f"/accounts/{user.pk}/")
    assert resp.status_code == HTML_REDIRECT_MOVED_PERMAMENTLY_CODE
    assert resp.url == f"/accounts/{user.username}/"


def test_profile_view_url_accessible_by_name(auto_login_user):
    client, user = auto_login_user()
    resp = client.get(reverse("user-detail", kwargs={"username": user.username}))
    assert resp.status_code == HTML_OK_CODE


def test_profile_view_uses_correct_template(auto_login_user):
    client, user = auto_login_user()
    resp = client.get(reverse("user-detail", kwargs={"username": user.username}))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "users/customuser_detail.html")


def test_user_list_view_url_exists(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/accounts/users/")
    assert resp.status_code == HTML_OK_CODE


def test_user_list_view_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("user-list"))
    assert resp.status_code == HTML_OK_CODE


def test_user_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("user-list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "users/customuser_list.html")


def test_user_search_view_accessible_by_name(auto_login_user):
    client, user = auto_login_user()
    resp = client.get(reverse("user-search"), {"q": user.username})
    assert resp.status_code == HTML_OK_CODE


def test_valid_form(db):
    form = CustomUserChangeForm(
        data={
            "username": "wsimonson",
            "first_name": "Walter",
            "last_name": "Simonson",
            "email": "wsimonson@test.com",
            "image": "user/walter.jpg",
        }
    )
    assert form.is_valid() is True


def test_form_invalid(db):
    form = CustomUserChangeForm(
        data={
            "username": "",
            "first_name": "bad-data",
            "last_name": "",
            "email": "",
            "image": "",
        }
    )
    assert form.is_valid() is False


# --- get_rate_limit_usage tests ---


def test_rate_limit_usage_no_history(create_user):
    user = create_user()
    cache.delete(f"throttle_sustained_{user.pk}")
    result = get_rate_limit_usage(user)
    assert result["used"] == 0
    assert result["remaining"] == SUSTAINED_LIMIT
    assert result["limit"] == SUSTAINED_LIMIT
    assert result["percent_used"] == 0.0


def test_rate_limit_usage_with_history(create_user):
    user = create_user()
    now = time.time()
    # Simulate 10 recent requests
    cache.set(f"throttle_sustained_{user.pk}", [now - i for i in range(10)])
    result = get_rate_limit_usage(user)
    assert result["used"] == 10
    assert result["remaining"] == SUSTAINED_LIMIT - 10
    cache.delete(f"throttle_sustained_{user.pk}")


def test_rate_limit_usage_filters_old_timestamps(create_user):
    user = create_user()
    now = time.time()
    recent = [now - 100, now - 200]
    old = [now - SUSTAINED_DURATION - 1, now - SUSTAINED_DURATION - 3600]
    cache.set(f"throttle_sustained_{user.pk}", recent + old)
    result = get_rate_limit_usage(user)
    assert result["used"] == 2
    cache.delete(f"throttle_sustained_{user.pk}")


def test_rate_limit_percent_used(create_user):
    user = create_user()
    now = time.time()
    used = 500
    cache.set(f"throttle_sustained_{user.pk}", [now - i for i in range(used)])
    result = get_rate_limit_usage(user)
    assert result["percent_used"] == round(used / SUSTAINED_LIMIT * 100, 1)
    cache.delete(f"throttle_sustained_{user.pk}")


# --- Profile view rate_limit context tests ---


def test_profile_view_includes_rate_limit_for_own_profile(auto_login_user):
    client, user = auto_login_user()
    resp = client.get(reverse("user-detail", kwargs={"username": user.username}))
    assert resp.status_code == HTML_OK_CODE
    assert "rate_limit" in resp.context
    assert resp.context["rate_limit"]["limit"] == SUSTAINED_LIMIT


def test_profile_view_excludes_rate_limit_for_other_profile(auto_login_user, create_user):
    client, _ = auto_login_user()
    other = create_user()
    resp = client.get(reverse("user-detail", kwargs={"username": other.username}))
    assert resp.status_code == HTML_OK_CODE
    assert "rate_limit" not in resp.context


# --- delete_account view tests ---


def test_delete_account_get_unauthenticated(client):
    resp = client.get(reverse("delete_account"))
    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert "/accounts/login/" in resp.url


def test_delete_account_get_authenticated(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("delete_account"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "users/delete_account.html")


def test_delete_account_post_unauthenticated(client, create_user):
    user = create_user()
    user_pk = user.pk
    resp = client.post(reverse("delete_account"))
    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert "/accounts/login/" in resp.url
    assert CustomUser.objects.filter(pk=user_pk).exists()


def test_delete_account_post_deletes_user(auto_login_user):
    client, user = auto_login_user()
    user_pk = user.pk
    resp = client.post(reverse("delete_account"))
    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert resp.url == reverse("home")
    assert not CustomUser.objects.filter(pk=user_pk).exists()


def test_delete_account_post_logs_out_user(auto_login_user):
    client, _ = auto_login_user()
    client.post(reverse("delete_account"))
    resp = client.get(reverse("change_profile"))
    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert "/accounts/login/" in resp.url


# --- api_tokens view tests ---


def test_api_tokens_get_unauthenticated(client):
    resp = client.get(reverse("api_tokens"))
    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert "/accounts/login/" in resp.url


def test_api_tokens_get_authenticated(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("api_tokens"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "users/api_token.html")


def test_api_tokens_post_creates_token(auto_login_user):
    client, user = auto_login_user()
    resp = client.post(reverse("api_tokens"), {"name": "Mokkari script"})
    assert resp.status_code == HTML_OK_CODE
    assert user.auth_token_set.count() == 1
    assert user.auth_token_set.get().name == "Mokkari script"
    assert resp.context["new_token"]


def test_api_tokens_post_name_is_optional(auto_login_user):
    client, user = auto_login_user()
    resp = client.post(reverse("api_tokens"), {"name": ""})
    assert resp.status_code == HTML_OK_CODE
    assert user.auth_token_set.get().name == ""


def test_api_tokens_new_token_not_shown_after_reload(auto_login_user):
    client, _user = auto_login_user()
    client.post(reverse("api_tokens"), {"name": "test"})
    resp = client.get(reverse("api_tokens"))
    assert resp.context["new_token"] is None


# --- revoke_api_token view tests ---


def test_revoke_api_token_unauthenticated(client):
    resp = client.post(reverse("revoke_api_token", kwargs={"digest": "abc"}))
    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert "/accounts/login/" in resp.url


def test_revoke_api_token_deletes_own_token(auto_login_user):
    client, user = auto_login_user()
    instance, _token = ApiToken.objects.create(user=user, name="test")

    resp = client.post(reverse("revoke_api_token", kwargs={"digest": instance.digest}))

    assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
    assert resp.url == reverse("api_tokens")
    assert not ApiToken.objects.filter(digest=instance.digest).exists()


def test_revoke_api_token_cannot_delete_other_users_token(auto_login_user, create_user):
    client, _user = auto_login_user()
    other_user = create_user()
    instance, _token = ApiToken.objects.create(user=other_user, name="test")

    resp = client.post(reverse("revoke_api_token", kwargs={"digest": instance.digest}))

    assert resp.status_code == HTTP_NOT_FOUND_CODE
    assert ApiToken.objects.filter(digest=instance.digest).exists()
