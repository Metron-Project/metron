"""Tracks which authentication method API requests use.

Part of the Basic Auth deprecation migration: lets us measure adoption of
token-based auth over time before removing Basic Auth entirely.
"""

import logging
from datetime import UTC, datetime

from django.core.cache import cache
from knox.auth import TokenAuthentication
from rest_framework.authentication import BasicAuthentication, SessionAuthentication

logger = logging.getLogger(__name__)

# Counters are keyed per day, so this is just cleanup headroom, not a retention window.
AUTH_METHOD_COUNTER_TTL = 60 * 60 * 24 * 35


def _client_ip(request):
    # nginx (nginx/nginx.conf) always overwrites X-Real-IP with its own
    # observed connecting address, so it's safe to trust - unlike
    # X-Forwarded-For, which nginx appends to rather than replaces, so it can
    # carry a client-supplied prefix. Falls back to REMOTE_ADDR for local dev
    # (runserver with no proxy in front, where there's no X-Real-IP header).
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "unknown")


def _classify_authenticator(authenticator):
    # isinstance, not class-name matching, so any future authenticator subclasses
    # are still classified correctly.
    if isinstance(authenticator, TokenAuthentication):
        return "token"
    if isinstance(authenticator, BasicAuthentication):
        return "basic"
    if isinstance(authenticator, SessionAuthentication):
        return "session"
    return "other"


def record_auth_method_usage(request, user):
    """Log and count which authenticator succeeded for this request."""
    authenticator = request.successful_authenticator
    if authenticator is None:
        return

    slug = _classify_authenticator(authenticator)

    today = datetime.now(UTC).date().isoformat()
    cache_key = f"authmethod:{slug}:{today}"
    cache.add(cache_key, 0, timeout=AUTH_METHOD_COUNTER_TTL)
    cache.incr(cache_key)

    ip = _client_ip(request)

    logger.info(
        "API request authenticated via %s (user=%s, ip=%s)",
        slug,
        user.username,
        ip,
        extra={"username": user.username, "auth_method": slug, "ip": ip},
    )
