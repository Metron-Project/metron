# ruff: noqa: S310
import json
import logging
import urllib.parse
import urllib.request

from metron import settings

logger = logging.getLogger(__name__)

HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"
# Without a timeout a stalled hCaptcha endpoint blocks the gunicorn worker
# indefinitely; fail fast instead, like the SMTP and database settings.
HCAPTCHA_TIMEOUT = 10
# Error code returned when hCaptcha itself couldn't be reached or answered with
# something unparseable, so callers can tell an outage apart from a failed check.
HCAPTCHA_UNAVAILABLE = "verification-unavailable"


def get_recaptcha_auth(request):
    hcaptcha_response = request.POST.get("h-captcha-response")
    values = {
        "secret": settings.HCAPTCHA_SECRET_KEY,
        "response": hcaptcha_response,
    }
    data = urllib.parse.urlencode(values).encode()
    req = urllib.request.Request(HCAPTCHA_VERIFY_URL, data=data)
    try:
        with urllib.request.urlopen(req, timeout=HCAPTCHA_TIMEOUT) as response:
            return json.loads(response.read().decode())
    # URLError and socket timeouts are OSError subclasses; JSONDecodeError and
    # UnicodeDecodeError are ValueError subclasses.
    except OSError, ValueError:
        logger.exception("hCaptcha verification request failed")
        return {"success": False, "error-codes": [HCAPTCHA_UNAVAILABLE]}
