import http.client
import json
import logging
import ssl
import time
import urllib.parse

from django.conf import settings
from django.core.cache import cache

LOGGER = logging.getLogger(__name__)

USERCHECK_HOST = "api.usercheck.com"
# Verdicts are about the domain, not the mailbox, so one lookup covers every
# address on it - caching them saves credits on the (metered) UserCheck plan.
CACHE_PREFIX = "usercheck:domain"
CACHE_TIMEOUT = 60 * 60 * 24 * 30
# The free plan allows 1 request/second, so a 429 is often just two lookups
# landing in the same second; one retry after this delay covers that.
RETRY_DELAY = 1
ALERT_KEY = "usercheck:alerted"
ALERT_INTERVAL = 60 * 60


def client_ip(request):
    # nginx (nginx/nginx.conf) always overwrites X-Real-IP with its own
    # observed connecting address, so it's safe to trust - unlike
    # X-Forwarded-For, which nginx appends to rather than replaces, so it can
    # carry a client-supplied prefix. Falls back to REMOTE_ADDR for local dev
    # (runserver with no proxy in front, where there's no X-Real-IP header).
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "unknown")


def _alert_usercheck_failure(reason: str) -> None:
    LOGGER.error("UserCheck lookup failed: %s", reason)
    # cache.add only succeeds once per interval, so an outage (or running out of
    # credits) sends one notification rather than one per signup attempt.
    if cache.add(ALERT_KEY, True, timeout=ALERT_INTERVAL):
        send_pushover(
            f"UserCheck email lookups are failing ({reason}). "
            "Signups are being allowed without the remote check."
        )


def _usercheck_request(email: str) -> tuple[int, str, bytes]:
    conn = None
    try:
        # Without a timeout a stalled API blocks the gunicorn worker indefinitely.
        conn = http.client.HTTPSConnection(USERCHECK_HOST, timeout=10)
        # Encode the address: a quoted local part may legally contain "/", "?", "#"
        # or spaces, which would otherwise alter or break the path.
        path = f"/email/{urllib.parse.quote(email, safe='')}"
        headers = {"Authorization": f"Bearer {settings.USERCHECK_API_KEY}"}
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        return res.status, res.reason, res.read()
    finally:
        if conn is not None:
            conn.close()


def check_email_domain(email: str) -> dict | None:
    """Look up ``email`` with UserCheck and return a verdict for its domain.

    The verdict has ``disposable``, ``spam``, ``relay_domain``, ``mx`` and
    ``suggested_domain`` keys, or is ``{"invalid": True}`` for an address UserCheck
    rejects as malformed. Returns None when no answer could be had (network error,
    out of credits, ...), leaving the caller to decide whether to fail open.
    """
    domain = email.rsplit("@", 1)[-1].lower()
    cache_key = f"{CACHE_PREFIX}:{domain}"
    if (cached := cache.get(cache_key)) is not None:
        return cached

    try:
        status, reason, body = _usercheck_request(email)
        if status == 429:  # noqa: PLR2004
            time.sleep(RETRY_DELAY)
            status, reason, body = _usercheck_request(email)
    except (http.client.HTTPException, OSError) as e:
        _alert_usercheck_failure(f"{type(e).__name__}: {e}")
        return None

    match status:
        case 200:
            try:
                data = json.loads(body.decode("utf-8"))
            except ValueError as e:
                _alert_usercheck_failure(f"invalid JSON: {e}")
                return None
            did_you_mean = data.get("did_you_mean")
            verdict = {
                "disposable": bool(data.get("disposable")),
                "spam": bool(data.get("spam")),
                "relay_domain": bool(data.get("relay_domain")),
                # None means UserCheck couldn't tell, which isn't grounds to reject.
                "mx": data.get("mx"),
                "suggested_domain": did_you_mean.rsplit("@", 1)[-1] if did_you_mean else None,
            }
            cache.set(cache_key, verdict, timeout=CACHE_TIMEOUT)
            return verdict
        case 400:
            # Specific to the address, so not cached.
            return {"invalid": True}
        case _:
            _alert_usercheck_failure(f"{status} {reason}")
            return None


def send_pushover(message):
    # PUSHOVER_USER_KEY may be a comma-separated list of user/group keys - Pushover's
    # API only accepts one recipient per request, so notify each in turn.
    user_keys = [key.strip() for key in settings.PUSHOVER_USER_KEY.split(",") if key.strip()]
    for user_key in user_keys:
        context = ssl.create_default_context()
        conn = http.client.HTTPSConnection("api.pushover.net:443", context=context)
        conn.request(
            "POST",
            "/1/messages.json",
            urllib.parse.urlencode(
                {
                    "token": settings.PUSHOVER_TOKEN,
                    "user": user_key,
                    "message": message,
                }
            ),
            {"Content-type": "application/x-www-form-urlencoded"},
        )
        conn.getresponse()
