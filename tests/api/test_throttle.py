import math
import time
from datetime import timedelta

import pytest
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from api.middleware import RateLimitHeadersMiddleware
from api.throttle import BurstRateThrottle

# ---------------------------------------------------------------------------
# Middleware unit tests (no database required)
# ---------------------------------------------------------------------------


def _make_middleware(response=None):
    if response is None:
        response = HttpResponse()
    return RateLimitHeadersMiddleware(get_response=lambda r: response), response


def test_middleware_adds_throttle_headers_to_response():
    request = RequestFactory().get("/")
    request._throttle_headers = {
        "X-RateLimit-Burst-Limit": "20",
        "X-RateLimit-Burst-Remaining": "19",
        "X-RateLimit-Burst-Reset": "1700000060",
    }
    middleware, _response = _make_middleware()
    result = middleware(request)
    assert result["X-RateLimit-Burst-Limit"] == "20"
    assert result["X-RateLimit-Burst-Remaining"] == "19"
    assert result["X-RateLimit-Burst-Reset"] == "1700000060"


def test_middleware_does_not_add_headers_when_none_set():
    request = RequestFactory().get("/")
    middleware, response = _make_middleware()
    middleware(request)
    assert "X-RateLimit-Burst-Limit" not in response
    assert "X-RateLimit-Sustained-Limit" not in response


# ---------------------------------------------------------------------------
# Integration tests — verify headers appear on real API responses
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_response_includes_burst_rate_limit_headers(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "X-RateLimit-Burst-Limit" in resp
    assert "X-RateLimit-Burst-Remaining" in resp
    assert "X-RateLimit-Burst-Reset" in resp


@pytest.mark.django_db
def test_response_includes_sustained_rate_limit_headers(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "X-RateLimit-Sustained-Limit" in resp
    assert "X-RateLimit-Sustained-Remaining" in resp
    assert "X-RateLimit-Sustained-Reset" in resp


@pytest.mark.django_db
def test_rate_limit_header_values_are_integers(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK
    for header in (
        "X-RateLimit-Burst-Limit",
        "X-RateLimit-Burst-Remaining",
        "X-RateLimit-Burst-Reset",
        "X-RateLimit-Sustained-Limit",
        "X-RateLimit-Sustained-Remaining",
        "X-RateLimit-Sustained-Reset",
    ):
        assert resp[header].isdigit(), f"{header} value {resp[header]!r} is not an integer"


@pytest.mark.django_db
def test_burst_remaining_decrements_on_successive_requests(api_client_with_credentials):
    resp1 = api_client_with_credentials.get(reverse("api:arc-list"))
    resp2 = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp1.status_code == status.HTTP_200_OK
    assert resp2.status_code == status.HTTP_200_OK
    remaining1 = int(resp1["X-RateLimit-Burst-Remaining"])
    remaining2 = int(resp2["X-RateLimit-Burst-Remaining"])
    assert remaining2 == remaining1 - 1


@pytest.mark.django_db
def test_sustained_remaining_decrements_on_successive_requests(api_client_with_credentials):
    resp1 = api_client_with_credentials.get(reverse("api:arc-list"))
    resp2 = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp1.status_code == status.HTTP_200_OK
    assert resp2.status_code == status.HTTP_200_OK
    remaining1 = int(resp1["X-RateLimit-Sustained-Remaining"])
    remaining2 = int(resp2["X-RateLimit-Sustained-Remaining"])
    assert remaining2 == remaining1 - 1


# ---------------------------------------------------------------------------
# Supporter (OpenCollective donor) elevated rate limit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_supporter_gets_elevated_sustained_limit(create_user, api_client):
    user = create_user()
    user.supporter_until = timezone.now() + timedelta(days=30)
    user.supporter_tier = "backer"
    user.save()
    api_client.force_authenticate(user=user)

    resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-RateLimit-Sustained-Limit"] == "10000"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("tier", "expected_limit"),
    [("friend", "7500"), ("backer", "10000"), ("sponsor", "15000"), ("mega_sponsor", "25000")],
)
def test_supporter_tier_sets_expected_sustained_limit(
    create_user, api_client, tier, expected_limit
):
    user = create_user()
    user.supporter_until = timezone.now() + timedelta(days=30)
    user.supporter_tier = tier
    user.save()
    api_client.force_authenticate(user=user)

    resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-RateLimit-Sustained-Limit"] == expected_limit


@pytest.mark.django_db
def test_supporter_with_blank_tier_falls_back_to_lowest_tier_limit(create_user, api_client):
    user = create_user()
    user.supporter_until = timezone.now() + timedelta(days=30)
    # supporter_tier left blank on purpose
    user.save()
    api_client.force_authenticate(user=user)

    resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-RateLimit-Sustained-Limit"] == "7500"


@pytest.mark.django_db
def test_superuser_gets_mega_sponsor_sustained_limit(create_user, api_client):
    user = create_user(is_superuser=True)
    api_client.force_authenticate(user=user)

    resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-RateLimit-Sustained-Limit"] == "25000"


@pytest.mark.django_db
def test_non_supporter_gets_default_sustained_limit(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-RateLimit-Sustained-Limit"] == "5000"


@pytest.mark.django_db
def test_expired_supporter_gets_default_sustained_limit(create_user, api_client):
    user = create_user()
    user.supporter_until = timezone.now() - timedelta(days=1)
    user.save()
    api_client.force_authenticate(user=user)

    resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    assert resp["X-RateLimit-Sustained-Limit"] == "5000"


# ---------------------------------------------------------------------------
# Over-limit history (limit lowered while a user is above the new one)
# ---------------------------------------------------------------------------

NOW = 1_700_000_000.0


def _throttle_with_history(num_requests, ages):
    """Build a burst throttle whose history holds requests made `ages` seconds ago."""
    throttle = BurstRateThrottle()
    throttle.num_requests = num_requests
    throttle.duration = 60
    throttle.now = NOW
    throttle.history = [NOW - age for age in sorted(ages)]  # newest first, like DRF
    return throttle


def test_wait_at_the_limit_is_time_until_oldest_entry_expires():
    throttle = _throttle_with_history(3, [5, 20, 40])
    assert throttle.wait() == pytest.approx(20)


def test_wait_over_the_limit_is_not_none():
    # 5 entries against a limit of 3: the 3rd-oldest (20s old) must expire before a
    # request fits, i.e. in 60 - 20 seconds.
    throttle = _throttle_with_history(3, [5, 10, 20, 40, 50])
    assert throttle.wait() == pytest.approx(40)


def test_wait_over_the_limit_grows_with_the_excess():
    # One more recent request means one more entry has to expire, so the wait is longer.
    assert _throttle_with_history(3, [5, 10, 20, 40, 50]).wait() == pytest.approx(40)
    assert _throttle_with_history(3, [2, 5, 10, 20, 40, 50]).wait() == pytest.approx(50)


def test_wait_with_no_history_falls_back_to_drf():
    throttle = _throttle_with_history(0, [])
    assert throttle.wait() == 60


@pytest.mark.django_db
def test_over_limit_429_includes_retry_after_and_accurate_reset(create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    burst_key = f"throttle_burst_{user.pk}"
    now = time.time()
    # 25 requests in the last 24s against a burst limit of 20 (newest first).
    history = [now - age for age in range(1, 26)]
    cache.set(burst_key, history, 60)

    try:
        resp = api_client.get(reverse("api:arc-list"))
    finally:
        cache.delete(burst_key)

    assert resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    # 6 entries must expire (25 - 20 + 1); the 6th oldest is 20s old.
    expected_wait = 60 - 20
    assert "Retry-After" in resp
    assert int(resp["Retry-After"]) == pytest.approx(expected_wait, abs=2)
    assert resp["X-RateLimit-Burst-Remaining"] == "0"
    assert int(resp["X-RateLimit-Burst-Reset"]) == pytest.approx(
        math.ceil(now + expected_wait), abs=2
    )
