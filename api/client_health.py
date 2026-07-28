"""Tracks API clients that don't back off after being rate-limited.

A client that keeps retrying after a 429 instead of backing off puts
unnecessary load on production. This logs and counts those events (per
user/day where a user can be identified) so the offending client can be
traced back to a specific account and contacted.
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Counters are keyed per day, so this is cleanup headroom, not a retention window.
CLIENT_HEALTH_COUNTER_TTL = 60 * 60 * 24 * 35

# Matches the tail of a `throttled:{scope}:user:{username}:{date}` cache key,
# regardless of the `:1:` version prefix Django's cache framework adds.
_THROTTLE_KEY_RE = re.compile(
    r"throttled:(?P<scope>[^:]+):user:(?P<username>[^:]+):(?P<date>[^:]+)$"
)


def _today():
    return datetime.now(UTC).date().isoformat()


def _request_identity(request):
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return f"user:{user.username}"
    return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"


def record_throttled_request(request, scope):
    """Called whenever a throttle denies a request (a 429 is about to be returned)."""
    identity = _request_identity(request)
    cache_key = f"throttled:{scope}:{identity}:{_today()}"
    cache.add(cache_key, 0, timeout=CLIENT_HEALTH_COUNTER_TTL)
    count = cache.incr(cache_key)

    logger.warning(
        "Request throttled (%s limit) for %s (%d today)",
        scope,
        identity,
        count,
        extra={"identity": identity, "scope": scope, "count": count},
    )


@dataclass
class RepeatOffender:
    username: str
    days_throttled: int
    total_count: int
    worst_day_count: int


def find_repeat_offenders(
    lookback_days: int = 7, min_days: int = 3, single_day_threshold: int = 50
) -> list[RepeatOffender]:
    """Scan the throttled-request counters for accounts that keep getting
    rate-limited without backing off: throttled on `min_days`+ distinct UTC days,
    or with any single day's count at or above `single_day_threshold`, within the
    last `lookback_days` days. IP-only identities (unauthenticated requests) are
    skipped - there's no account to contact.

    Django's cache framework has no key-scanning API, so this drops to the
    underlying redis-py client (the same one the cache backend itself uses) to
    SCAN for matching keys.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=lookback_days)).date()
    client = cache._cache.get_client(write=False)

    daily_counts_by_user: dict[str, dict[str, int]] = defaultdict(dict)
    for raw_key in client.scan_iter(match="*throttled:*:user:*"):
        key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
        match = _THROTTLE_KEY_RE.search(key)
        if not match:
            continue

        date_str = match["date"]
        try:
            day = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day < cutoff:
            continue

        value = client.get(raw_key)
        if value is None:
            continue

        username = match["username"]
        daily_counts_by_user[username][date_str] = daily_counts_by_user[username].get(
            date_str, 0
        ) + int(value)

    offenders = []
    for username, daily_counts in daily_counts_by_user.items():
        days_throttled = len(daily_counts)
        worst_day_count = max(daily_counts.values())
        if days_throttled >= min_days or worst_day_count >= single_day_threshold:
            offenders.append(
                RepeatOffender(
                    username=username,
                    days_throttled=days_throttled,
                    total_count=sum(daily_counts.values()),
                    worst_day_count=worst_day_count,
                )
            )
    return offenders
