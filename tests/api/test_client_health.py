import uuid
from datetime import UTC, datetime, timedelta

import pytest
from django.core.cache import cache
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status

from api.client_health import find_repeat_offenders, record_throttled_request

TODAY = datetime.now(UTC).date().isoformat()


def _date_str(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).date().isoformat()


def _set_count(scope: str, identity: str, days_ago: int, count: int) -> None:
    key = f"throttled:{scope}:{identity}:{_date_str(days_ago)}"
    cache.set(key, count, timeout=60 * 60 * 24 * 35)


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


# ---------------------------------------------------------------------------
# find_repeat_offenders — unit tests. Each test uses a unique username so it's
# safe against the real (shared) cache backend without needing isolation.
# ---------------------------------------------------------------------------


def test_finds_user_with_min_days_at_or_above_threshold():
    username = _unique()
    for days_ago in (0, 1, 2):
        _set_count("burst", f"user:{username}", days_ago, 60)

    offenders = find_repeat_offenders(lookback_days=7, min_days=3, single_day_threshold=50)

    matches = [o for o in offenders if o.username == username]
    assert len(matches) == 1
    assert matches[0].days_throttled == 3
    assert matches[0].total_count == 180
    assert matches[0].worst_day_count == 60


def test_ignores_user_with_too_few_days_at_threshold():
    username = _unique()
    # Only 2 of the 3 required days reach the threshold.
    for days_ago in (0, 1):
        _set_count("burst", f"user:{username}", days_ago, 60)
    _set_count("burst", f"user:{username}", 2, 5)

    offenders = find_repeat_offenders(lookback_days=7, min_days=3, single_day_threshold=50)

    assert all(o.username != username for o in offenders)


def test_ignores_user_with_many_low_volume_days():
    # A user throttled on min_days+ days, but never at the per-day threshold,
    # shouldn't be flagged - low-volume repeated throttling isn't worth an email.
    username = _unique()
    for days_ago in (0, 1, 2):
        _set_count("burst", f"user:{username}", days_ago, 3)

    offenders = find_repeat_offenders(lookback_days=7, min_days=3, single_day_threshold=50)

    assert all(o.username != username for o in offenders)


def test_single_bad_day_below_extreme_threshold_does_not_trigger_alone():
    # A single day above single_day_threshold but below extreme_day_threshold
    # shouldn't flag an account on its own - it takes min_days separate days.
    username = _unique()
    _set_count("sustained", f"user:{username}", 0, 90)

    offenders = find_repeat_offenders(
        lookback_days=7, min_days=3, single_day_threshold=50, extreme_day_threshold=100
    )

    assert all(o.username != username for o in offenders)


def test_extreme_single_day_triggers_alone():
    # A single day at or above extreme_day_threshold flags the account outright,
    # even though it's only one day (well short of min_days).
    username = _unique()
    _set_count("sustained", f"user:{username}", 0, 150)

    offenders = find_repeat_offenders(
        lookback_days=7, min_days=3, single_day_threshold=50, extreme_day_threshold=100
    )

    matches = [o for o in offenders if o.username == username]
    assert len(matches) == 1
    assert matches[0].days_throttled == 1
    assert matches[0].worst_day_count == 150


def test_ignores_dates_outside_lookback_window():
    username = _unique()
    _set_count("burst", f"user:{username}", 40, 1000)

    offenders = find_repeat_offenders(lookback_days=7, min_days=1, single_day_threshold=1)

    assert all(o.username != username for o in offenders)


def test_ignores_ip_identities():
    ip = f"203.0.113.{uuid.uuid4().int % 255}"
    _set_count("burst", f"ip:{ip}", 0, 1000)

    offenders = find_repeat_offenders(lookback_days=7, min_days=1, single_day_threshold=1)

    assert all(ip not in o.username for o in offenders)


def test_sums_counts_across_scopes_for_the_same_day():
    username = _unique()
    _set_count("burst", f"user:{username}", 0, 3)
    _set_count("sustained", f"user:{username}", 0, 4)

    offenders = find_repeat_offenders(lookback_days=7, min_days=1, single_day_threshold=1)

    matches = [o for o in offenders if o.username == username]
    assert len(matches) == 1
    assert matches[0].days_throttled == 1
    assert matches[0].total_count == 7
