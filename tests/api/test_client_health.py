import uuid
from datetime import UTC, datetime

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status

from api.client_health import record_throttled_request

TODAY = datetime.now(UTC).date().isoformat()


class DummyUser:
    def __init__(self, username, is_authenticated=True):
        self.username = username
        self.is_authenticated = is_authenticated


def _unique():
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Unit tests. Cache keys are scoped by a unique identity per call, so these
# are safe against the real (shared) cache backend without needing isolation.
# ---------------------------------------------------------------------------


def test_record_throttled_request_counts_authenticated_user():
    username = _unique()
    request = RequestFactory().get("/")
    request.user = DummyUser(username)

    record_throttled_request(request, "burst")

    assert cache.get(f"throttled:burst:user:{username}:{TODAY}") == 1


def test_record_throttled_request_counts_anonymous_by_ip():
    # Unique-per-test IP (rather than a fixed address) so repeated local runs
    # against the same day don't accumulate a stale count from a prior run.
    ip = f"203.0.113.{uuid.uuid4().int % 255}"
    cache_key = f"throttled:sustained:ip:{ip}:{TODAY}"
    cache.delete(cache_key)
    request = RequestFactory().get("/", REMOTE_ADDR=ip)
    request.user = DummyUser("irrelevant", is_authenticated=False)

    record_throttled_request(request, "sustained")

    assert cache.get(cache_key) == 1


def test_record_throttled_request_increments_on_repeat():
    username = _unique()
    request = RequestFactory().get("/")
    request.user = DummyUser(username)

    record_throttled_request(request, "burst")
    record_throttled_request(request, "burst")

    assert cache.get(f"throttled:burst:user:{username}:{TODAY}") == 2


# ---------------------------------------------------------------------------
# Integration test — verify a real throttled request is tracked.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_exceeding_burst_limit_returns_429_and_is_tracked(create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    # DRF's own burst-throttle history is Redis-backed and keyed by user pk, which
    # test-db recreation recycles across runs — clear any stale leftover history
    # for this pk so the test starts from a known-clean state.
    burst_key = f"throttle_burst_{user.pk}"
    cache.delete(burst_key)

    try:
        for _ in range(20):
            resp = api_client.get(reverse("api:arc-list"))
            assert resp.status_code == status.HTTP_200_OK
        throttled_resp = api_client.get(reverse("api:arc-list"))

        assert throttled_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert cache.get(f"throttled:burst:user:{user.username}:{TODAY}") == 1
    finally:
        # Don't leave this pk's burst history exhausted for whatever test/run
        # recycles it next.
        cache.delete(burst_key)
