"""Cache-based limits on failed password attempts.

Counts failures per (username, IP) and per IP within a fixed window. Only the pair
and the IP are ever locked, never a username on its own, so someone guessing from
elsewhere can't lock a real user out of their account.

Used by RateLimitedModelBackend for every login path (site, admin, browsable API
login and API Basic auth), and by forms that re-check the current password, so
those can't be used to guess it either. Like the rest of the cache, the limits
fail open while Redis is unavailable (see metron.cache_backends).
"""

import hashlib

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from users.utils import client_ip

FAILURE_WINDOW = 15 * 60  # seconds
USER_IP_FAILURE_LIMIT = 5
IP_FAILURE_LIMIT = 20
KEY_PREFIX = "login_fail"
# Set on the request when a login was refused for being locked, so login forms can
# say so instead of reporting a wrong password.
LOCKED_REQUEST_ATTR = "login_throttled"
LOCKED_MESSAGE = _("Too many failed attempts. Please try again in 15 minutes.")


def _keys(request, username):
    ip = client_ip(request)
    # Hashed so arbitrary usernames are safe to use in a cache key.
    user_hash = hashlib.sha256(str(username).lower().encode()).hexdigest()[:32]
    return f"{KEY_PREFIX}:ip:{ip}", f"{KEY_PREFIX}:user_ip:{user_hash}:{ip}"


def is_locked(request, username) -> bool:
    ip_key, pair_key = _keys(request, username)
    return (
        cache.get(ip_key, 0) >= IP_FAILURE_LIMIT or cache.get(pair_key, 0) >= USER_IP_FAILURE_LIMIT
    )


def record_failure(request, username) -> None:
    for key in _keys(request, username):
        # The window starts at the first failure; add() is a no-op once it exists.
        cache.add(key, 0, timeout=FAILURE_WINDOW)
        try:
            cache.incr(key)
        except ValueError:
            # Expired between add() and incr(); start a fresh window.
            cache.add(key, 1, timeout=FAILURE_WINDOW)


def record_success(request, username) -> None:
    # Only the pair is cleared. The IP count stays, so logging in to one account
    # doesn't reset the budget for guessing others from the same address.
    _ip_key, pair_key = _keys(request, username)
    cache.delete(pair_key)


def check_password(request, user, password) -> bool | None:
    """Check ``user``'s password, subject to the same limits as logging in.

    Returns True or False, or None if the attempt was refused because the
    user/IP is locked (the password isn't checked at all then). Without a request
    there's no IP to attribute the attempt to, so it isn't limited.
    """
    if request is None:
        return user.check_password(password)
    if is_locked(request, user.get_username()):
        return None
    if user.check_password(password):
        record_success(request, user.get_username())
        return True
    record_failure(request, user.get_username())
    return False
