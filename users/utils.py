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
# Lookups run inside the signup request, so keep this short: a healthy lookup
# takes well under a second, and if it's slower we fail open anyway.
REQUEST_TIMEOUT = 3
# Verdicts are about the domain, not the mailbox, so one lookup covers every
# address on it - caching them saves credits on the (metered) UserCheck plan.
CACHE_PREFIX = "usercheck:domain"
CACHE_TIMEOUT = 60 * 60 * 24 * 30
# A missing MX record can be a passing DNS failure, and caching it for the full
# period would block every address on the domain until it expired.
NO_MX_CACHE_TIMEOUT = 60 * 60
# The free plan allows 1 request/second, so a 429 is often just two lookups
# landing in the same second; one retry after this delay covers that.
RETRY_DELAY = 1
ALERT_KEY = "usercheck:alerted"
ALERT_INTERVAL = 60 * 60
# Whether the plan has credits left, from the /status endpoint - only consulted
# when lookups keep getting a 429, so a short cache is plenty.
CREDITS_KEY = "usercheck:has_credits"
CREDITS_CACHE_TIMEOUT = 60 * 10
# The error UserCheck documents for its only 400: a malformed address. Any other
# 400 points at our request (or an API change), which mustn't block the user.
MALFORMED_EMAIL_ERROR = "The email address is invalid."


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
        # This runs when the network is likely unhealthy, so Pushover may be
        # failing too - that mustn't turn the caller's fail-open into a 500.
        try:
            send_pushover(
                f"UserCheck email lookups are failing ({reason}). "
                "Signups are being allowed without the remote check."
            )
        except http.client.HTTPException, OSError:
            LOGGER.exception("Failed to send UserCheck failure alert")


def _usercheck_request(path: str) -> tuple[int, str, bytes]:
    conn = None
    try:
        # Without a timeout a stalled API blocks the gunicorn worker indefinitely.
        conn = http.client.HTTPSConnection(USERCHECK_HOST, timeout=REQUEST_TIMEOUT)
        headers = {"Authorization": f"Bearer {settings.USERCHECK_API_KEY}"}
        conn.request("GET", path, headers=headers)
        res = conn.getresponse()
        return res.status, res.reason, res.read()
    finally:
        if conn is not None:
            conn.close()


def _has_credits() -> bool | None:
    """Whether the UserCheck plan has credits left, or None if that can't be told.

    The /email endpoint answers 429 both for the per-second limit and for an
    exhausted monthly quota, with identical bodies; /status tells them apart.
    """
    if (cached := cache.get(CREDITS_KEY)) is not None:
        return cached
    try:
        status, reason, body = _usercheck_request("/status")
        data = json.loads(body.decode("utf-8")) if status == 200 else None  # noqa: PLR2004
    except (http.client.HTTPException, OSError, ValueError) as e:
        LOGGER.warning("UserCheck status lookup failed: %s: %s", type(e).__name__, e)
        return None
    usage = data.get("usage") if isinstance(data, dict) else None
    remaining = usage.get("remaining") if isinstance(usage, dict) else None
    if not isinstance(remaining, int | float):
        LOGGER.warning("UserCheck status lookup failed: %s %s", status, reason)
        return None
    has_credits = remaining > 0
    cache.set(CREDITS_KEY, has_credits, timeout=CREDITS_CACHE_TIMEOUT)
    return has_credits


def _is_malformed_email_error(body: bytes) -> bool:
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError:
        return False
    return isinstance(data, dict) and data.get("error") == MALFORMED_EMAIL_ERROR


def _parse_verdict(body: bytes) -> dict | None:
    try:
        data = json.loads(body.decode("utf-8"))
    except ValueError as e:
        _alert_usercheck_failure(f"invalid JSON: {e}")
        return None
    if not isinstance(data, dict):
        _alert_usercheck_failure(f"unexpected response: {type(data).__name__}")
        return None
    did_you_mean = data.get("did_you_mean")
    if not isinstance(did_you_mean, str):
        did_you_mean = None
    return {
        "disposable": bool(data.get("disposable")),
        "spam": bool(data.get("spam")),
        "relay_domain": bool(data.get("relay_domain")),
        # None means UserCheck couldn't tell, which isn't grounds to reject.
        "mx": data.get("mx"),
        "suggested_domain": did_you_mean.rsplit("@", 1)[-1] if did_you_mean else None,
    }


def check_email_domain(email: str, domain: str) -> dict | None:
    """Look up ``email`` with UserCheck and return a verdict for its domain.

    ``domain`` is the caller's already-normalized (lowercased) domain of ``email``,
    used as the cache key so it matches what the caller checked its blocklists with.

    The verdict has ``disposable``, ``spam``, ``relay_domain``, ``mx`` and
    ``suggested_domain`` keys, or is ``{"invalid": True}`` for an address UserCheck
    rejects as malformed, or ``{"rate_limited": True}`` when lookups are still being
    throttled after a retry although the plan has credits left. Returns None when no
    answer could be had (network error, out of credits, ...), leaving the caller to
    decide whether to fail open.
    """
    if not settings.USERCHECK_API_KEY:
        LOGGER.warning("USERCHECK_API_KEY is not set; skipping UserCheck lookup")
        return None

    cache_key = f"{CACHE_PREFIX}:{domain}"
    if (cached := cache.get(cache_key)) is not None:
        return cached

    # Encode the address: a quoted local part may legally contain "/", "?", "#"
    # or spaces, which would otherwise alter or break the path.
    path = f"/email/{urllib.parse.quote(email, safe='')}"
    try:
        status, reason, body = _usercheck_request(path)
        if status == 429:  # noqa: PLR2004
            time.sleep(RETRY_DELAY)
            status, reason, body = _usercheck_request(path)
    except (http.client.HTTPException, OSError) as e:
        _alert_usercheck_failure(f"{type(e).__name__}: {e}")
        return None

    return _verdict_from_response(status, reason, body, cache_key)


def _verdict_from_response(status: int, reason: str, body: bytes, cache_key: str) -> dict | None:
    match status:
        case 200:
            verdict = _parse_verdict(body)
            if verdict is not None:
                timeout = NO_MX_CACHE_TIMEOUT if verdict["mx"] is False else CACHE_TIMEOUT
                cache.set(cache_key, verdict, timeout=timeout)
            return verdict
        case 400 if _is_malformed_email_error(body):
            # Specific to the address, so not cached.
            return {"invalid": True}
        case 429 if _has_credits():
            # Credits remain, so this is the per-second limit rather than an exhausted
            # quota. Failing open here would let anyone who can trigger it (by flooding
            # lookups) skip the check, so the caller asks the user to retry instead.
            LOGGER.warning("UserCheck lookups are still rate-limited after a retry")
            return {"rate_limited": True}
        case _:
            # Includes a 429 from an exhausted quota (or one /status couldn't explain),
            # and a 400 for anything other than a malformed address.
            _alert_usercheck_failure(f"{status} {reason}")
            return None


def send_pushover(message):
    # PUSHOVER_USER_KEY may be a comma-separated list of user/group keys - Pushover's
    # API only accepts one recipient per request, so notify each in turn.
    user_keys = [key.strip() for key in settings.PUSHOVER_USER_KEY.split(",") if key.strip()]
    for user_key in user_keys:
        context = ssl.create_default_context()
        conn = http.client.HTTPSConnection("api.pushover.net:443", context=context, timeout=10)
        try:
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
        finally:
            conn.close()
