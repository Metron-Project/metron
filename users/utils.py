import http.client
import json
import logging
import ssl
import urllib.parse

from django.conf import settings

from metron.settings import RAPID_API_HOST, RAPID_API_KEY

LOGGER = logging.getLogger(__name__)


def check_email_domain(email: str):
    result = None
    try:
        conn = http.client.HTTPSConnection("mailcheck.p.rapidapi.com")

        headers = {
            "X-RapidAPI-Key": RAPID_API_KEY,
            "X-RapidAPI-Host": RAPID_API_HOST,
        }

        conn.request("GET", f"/?domain={email}", headers=headers)

        res = conn.getresponse()
        match res.status:
            case 200:
                data = res.read()
                result = json.loads(data.decode("utf-8"))
            case _:
                LOGGER.error("Bad response from RapidAPI: %s %s", res.status, res.reason)
    except http.client.HTTPException as e:
        LOGGER.error("HTTP error: %s", e)
    except Exception as e:  # NOQA: BLE001
        LOGGER.error("An error occurred: %s", e)
    finally:
        conn.close()

    return result


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
