"""Tracks API clients that don't back off after being rate-limited.

A client that keeps retrying after a 429 instead of backing off puts
unnecessary load on production. This logs and counts those events (per
user/day where a user can be identified) so the offending client can be
traced back to a specific account and contacted.
"""

import logging
from datetime import UTC, datetime

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Counters are keyed per day, so this is cleanup headroom, not a retention window.
CLIENT_HEALTH_COUNTER_TTL = 60 * 60 * 24 * 35


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
