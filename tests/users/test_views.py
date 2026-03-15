import time

import pytest
from django.core.cache import cache
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from users.forms import CustomUserChangeForm
from users.views import SUSTAINED_DURATION, SUSTAINED_LIMIT, get_rate_limit_usage

HTML_REDIRECT_CODE = 301
HTML_OK_CODE = 200


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


def test_profile_view_url_exists_at_desired_location(auto_login_user):
    client, user = auto_login_user()
    resp = client.get(f"/accounts/{user.username}/")
    assert resp.status_code == HTML_OK_CODE


def test_profile_view_pk_redirects_to_username(auto_login_user):
    client, user = auto_login_user()
    resp = client.get(f"/accounts/{user.pk}/")
    assert resp.status_code == HTML_REDIRECT_CODE
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
