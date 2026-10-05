"""Tests for rate-limiting failed password attempts (users.login_throttle)."""

import base64

from django.contrib import admin
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status

from users import login_throttle
from users.admin import CustomUserAdmin
from users.models import CustomUser

HTML_OK_CODE = 200
HTTP_REDIRECT_FOUND_CODE = 302
LOCKED_TEXT = "Too many failed attempts"
NEW_EMAIL = "new-address@gmail.com"  # Allowlisted domain: skips the RapidAPI check.


def _login(client, username, password, ip="203.0.113.10"):
    return client.post(
        reverse("login"), {"username": username, "password": password}, REMOTE_ADDR=ip
    )


def _fail_logins(client, username, count, ip="203.0.113.10"):
    for _ in range(count):
        resp = _login(client, username, "wrong-password", ip=ip)
        assert resp.status_code == HTML_OK_CODE


class TestSiteLogin:
    def test_correct_password_refused_after_limit(self, client, create_user, test_password):
        user = create_user()
        _fail_logins(client, user.username, login_throttle.USER_IP_FAILURE_LIMIT)

        resp = _login(client, user.username, test_password)
        assert resp.status_code == HTML_OK_CODE
        assert LOCKED_TEXT in resp.content.decode()
        assert "_auth_user_id" not in client.session

    def test_below_limit_still_logs_in(self, client, create_user, test_password):
        user = create_user()
        _fail_logins(client, user.username, login_throttle.USER_IP_FAILURE_LIMIT - 1)

        resp = _login(client, user.username, test_password)
        assert resp.status_code == HTTP_REDIRECT_FOUND_CODE
        assert int(client.session["_auth_user_id"]) == user.pk

    def test_username_is_not_locked_from_other_ips(self, client, create_user, test_password):
        """Failures from one address must not lock the real user out elsewhere."""
        user = create_user()
        _fail_logins(client, user.username, login_throttle.USER_IP_FAILURE_LIMIT)

        resp = _login(client, user.username, test_password, ip="198.51.100.7")
        assert resp.status_code == HTTP_REDIRECT_FOUND_CODE

    def test_success_resets_the_user_ip_count(self, client, create_user, test_password):
        user = create_user()
        _fail_logins(client, user.username, login_throttle.USER_IP_FAILURE_LIMIT - 1)
        assert _login(client, user.username, test_password).status_code == 302
        client.logout()

        _fail_logins(client, user.username, login_throttle.USER_IP_FAILURE_LIMIT - 1)
        assert _login(client, user.username, test_password).status_code == 302

    def test_ip_locked_after_failures_across_usernames(self, client, create_user, test_password):
        user = create_user()
        per_name = login_throttle.USER_IP_FAILURE_LIMIT - 1
        for i in range(login_throttle.IP_FAILURE_LIMIT // per_name):
            _fail_logins(client, f"guess-{i}", per_name)

        resp = _login(client, user.username, test_password)
        assert LOCKED_TEXT in resp.content.decode()
        # The same account from another address is unaffected.
        assert _login(client, user.username, test_password, ip="198.51.100.7").status_code == 302

    def test_case_variants_share_a_count(self, client, create_user, test_password):
        create_user(username="CaseUser")
        _fail_logins(client, "caseuser", login_throttle.USER_IP_FAILURE_LIMIT)

        resp = _login(client, "CaseUser", test_password)
        assert LOCKED_TEXT in resp.content.decode()

    def test_uses_x_real_ip(self, client, create_user, test_password):
        """Behind nginx, REMOTE_ADDR is the proxy; X-Real-IP is the client."""
        user = create_user()
        for i in range(login_throttle.USER_IP_FAILURE_LIMIT):
            client.post(
                reverse("login"),
                {"username": user.username, "password": "wrong-password"},
                REMOTE_ADDR=f"10.0.0.{i}",
                HTTP_X_REAL_IP="203.0.113.99",
            )
        resp = client.post(
            reverse("login"),
            {"username": user.username, "password": test_password},
            REMOTE_ADDR="10.0.0.200",
            HTTP_X_REAL_IP="203.0.113.99",
        )
        assert LOCKED_TEXT in resp.content.decode()


def test_admin_login_is_limited(client, create_staff_user, test_password):
    user = create_staff_user
    url = reverse("admin:login")
    for _ in range(login_throttle.USER_IP_FAILURE_LIMIT):
        client.post(url, {"username": user.username, "password": "wrong-password"})

    resp = client.post(url, {"username": user.username, "password": test_password})
    assert resp.status_code == HTML_OK_CODE
    assert LOCKED_TEXT in resp.content.decode()
    assert "_auth_user_id" not in client.session


def test_api_basic_auth_is_limited(api_client, create_user, test_password):
    user = create_user()

    def get_with(password):
        token = base64.b64encode(f"{user.username}:{password}".encode()).decode()
        return api_client.get(reverse("api:publisher-list"), HTTP_AUTHORIZATION=f"Basic {token}")

    assert get_with(test_password).status_code == status.HTTP_200_OK
    for _ in range(login_throttle.USER_IP_FAILURE_LIMIT):
        assert get_with("wrong-password").status_code == status.HTTP_401_UNAUTHORIZED

    assert get_with(test_password).status_code == status.HTTP_401_UNAUTHORIZED


class TestAccountFormPasswordChecks:
    def test_profile_email_change_is_limited(self, auto_login_user, test_password):
        client, user = auto_login_user()
        data = {"username": user.username, "email": NEW_EMAIL, "bio": ""}
        url = reverse("change_profile")
        for _ in range(login_throttle.USER_IP_FAILURE_LIMIT):
            client.post(url, {**data, "current_password": "wrong-password"})

        resp = client.post(url, {**data, "current_password": test_password})
        assert resp.status_code == HTML_OK_CODE
        assert LOCKED_TEXT in str(resp.context["form"].errors["current_password"])
        user.refresh_from_db()
        assert user.email != NEW_EMAIL

    def test_delete_account_is_limited(self, auto_login_user, test_password):
        client, user = auto_login_user()
        url = reverse("delete_account")
        for _ in range(login_throttle.USER_IP_FAILURE_LIMIT):
            client.post(url, {"password": "wrong-password"})

        resp = client.post(url, {"password": test_password})
        assert resp.status_code == HTML_OK_CODE
        assert LOCKED_TEXT in str(resp.context["form"].errors["password"])
        assert CustomUser.objects.filter(pk=user.pk).exists()

    def test_form_failures_count_toward_login_limit(self, auto_login_user, client, test_password):
        """Guesses through the account forms and the login form share one budget."""
        client, user = auto_login_user()
        for _ in range(login_throttle.USER_IP_FAILURE_LIMIT):
            client.post(reverse("delete_account"), {"password": "wrong-password"})
        client.logout()

        resp = client.post(reverse("login"), {"username": user.username, "password": test_password})
        assert LOCKED_TEXT in resp.content.decode()


def test_admin_can_change_a_users_email_directly(create_user):
    """The admin user form must not inherit the profile form's password/confirm rules."""
    superuser = CustomUser.objects.create_superuser("root", "root@gmail.com", "pw")
    user = create_user()
    request = RequestFactory().get("/")
    request.user = superuser

    form_class = CustomUserAdmin(CustomUser, admin.site).get_form(request, obj=user)
    initial_form = form_class(instance=user)
    data = {}
    for name in initial_form.fields:
        value = initial_form[name].value()
        if value is None:
            continue
        data[name] = list(value) if isinstance(value, (list, tuple)) else value
    data["email"] = NEW_EMAIL

    form = form_class(data=data, instance=user)
    assert form.is_valid(), form.errors
    form.save()
    user.refresh_from_db()
    assert user.email == NEW_EMAIL


def test_check_password_without_request_is_unthrottled(create_user, test_password):
    user = create_user()
    for _ in range(login_throttle.USER_IP_FAILURE_LIMIT + 1):
        assert login_throttle.check_password(None, user, "wrong-password") is False
    assert login_throttle.check_password(None, user, test_password) is True
