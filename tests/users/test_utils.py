"""Tests for users.utils helpers."""

import json
from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache

from users.utils import CACHE_TIMEOUT, NO_MX_CACHE_TIMEOUT, check_email_domain

HTTPS_CONNECTION = "users.utils.http.client.HTTPSConnection"
SLEEP = "users.utils.time.sleep"
PUSHOVER = "users.utils.send_pushover"

USERCHECK_BODY = {
    "status": 200,
    "email": "x@example.org",
    "domain": "example.org",
    "mx": True,
    "disposable": False,
    "public_domain": False,
    "relay_domain": False,
    "spam": False,
    "did_you_mean": None,
}


@pytest.fixture(autouse=True)
def usercheck_api_key(settings):
    settings.USERCHECK_API_KEY = "test-key"


def _mock_connection(*statuses, body=None):
    """A connection whose successive responses have the given statuses (default: one 200)."""
    conn = MagicMock()
    responses = []
    for status in statuses or (200,):
        response = MagicMock()
        response.status = status
        response.reason = "OK" if status == 200 else "Error"
        response.read.return_value = json.dumps(
            (body or USERCHECK_BODY) if status == 200 else {"status": status, "error": "Error"}
        ).encode()
        responses.append(response)
    conn.getresponse.side_effect = responses
    return conn


@pytest.mark.parametrize(
    ("email", "expected_path"),
    [
        ("someone@example.org", "/email/someone%40example.org"),
        # A quoted local part may contain characters that are special in a path.
        ('"a/b?c#d"@example.org', "/email/%22a%2Fb%3Fc%23d%22%40example.org"),
        ('"first last"@example.org', "/email/%22first%20last%22%40example.org"),
    ],
)
def test_check_email_domain_encodes_path(email, expected_path):
    conn = _mock_connection()
    with patch(HTTPS_CONNECTION, return_value=conn):
        check_email_domain(email, "example.org")

    method, path = conn.request.call_args.args
    assert method == "GET"
    assert path == expected_path


def test_check_email_domain_sends_bearer_token(settings):
    settings.USERCHECK_API_KEY = "secret"
    conn = _mock_connection()
    with patch(HTTPS_CONNECTION, return_value=conn):
        check_email_domain("x@example.org", "example.org")

    assert conn.request.call_args.kwargs["headers"] == {"Authorization": "Bearer secret"}


def test_check_email_domain_returns_normalized_verdict():
    body = {
        **USERCHECK_BODY,
        "disposable": True,
        "relay_domain": True,
        "mx": False,
        "did_you_mean": "x@gmail.com",
    }
    with patch(HTTPS_CONNECTION, return_value=_mock_connection(body=body)):
        assert check_email_domain("x@gmial.com", "gmial.com") == {
            "disposable": True,
            "spam": False,
            "relay_domain": True,
            "mx": False,
            "suggested_domain": "gmail.com",
        }


def test_check_email_domain_caches_verdict_per_domain():
    conn = _mock_connection()
    with patch(HTTPS_CONNECTION, return_value=conn) as mock_conn:
        first = check_email_domain("x@example.org", "example.org")
        # Another mailbox on the same domain hits the cache.
        second = check_email_domain("y@example.org", "example.org")

    assert first == second
    mock_conn.assert_called_once()


@pytest.mark.parametrize(
    ("mx", "expected_timeout"),
    [(True, CACHE_TIMEOUT), (None, CACHE_TIMEOUT), (False, NO_MX_CACHE_TIMEOUT)],
)
def test_check_email_domain_caches_missing_mx_briefly(mx, expected_timeout):
    body = {**USERCHECK_BODY, "mx": mx}
    with (
        patch(HTTPS_CONNECTION, return_value=_mock_connection(body=body)),
        patch.object(cache, "set") as mock_set,
    ):
        check_email_domain("x@example.org", "example.org")
    assert mock_set.call_args.kwargs["timeout"] == expected_timeout


def test_check_email_domain_does_not_cache_failures():
    with patch(HTTPS_CONNECTION, side_effect=[_mock_connection(500), _mock_connection()]):
        assert check_email_domain("x@example.org", "example.org") is None
        assert check_email_domain("x@example.org", "example.org") is not None


def test_check_email_domain_flags_malformed_address():
    with patch(HTTPS_CONNECTION, return_value=_mock_connection(400)):
        assert check_email_domain("x@example.org", "example.org") == {"invalid": True}


def test_check_email_domain_retries_once_when_rate_limited():
    with (
        patch(HTTPS_CONNECTION, side_effect=[_mock_connection(429), _mock_connection()]),
        patch(SLEEP) as mock_sleep,
        patch(PUSHOVER) as mock_pushover,
    ):
        assert check_email_domain("x@example.org", "example.org") is not None

    mock_sleep.assert_called_once()
    mock_pushover.assert_not_called()


def _mock_status(remaining=None, status=200):
    """A connection answering the /status endpoint with ``remaining`` credits."""
    conn = MagicMock()
    response = conn.getresponse.return_value
    response.status = status
    response.reason = "OK" if status == 200 else "Error"
    response.read.return_value = json.dumps({"usage": {"remaining": remaining}}).encode()
    return conn


def test_check_email_domain_rejects_when_rate_limited_with_credits_left():
    status_conn = _mock_status(remaining=500)
    with (
        patch(
            HTTPS_CONNECTION,
            side_effect=[_mock_connection(429), _mock_connection(429), status_conn],
        ),
        patch(SLEEP),
        patch(PUSHOVER) as mock_pushover,
    ):
        assert check_email_domain("x@example.org", "example.org") == {"rate_limited": True}

    assert status_conn.request.call_args.args[:2] == ("GET", "/status")
    mock_pushover.assert_not_called()


@pytest.mark.parametrize(
    "status_conn",
    [
        _mock_status(remaining=0),  # quota exhausted
        _mock_status(status=500),  # /status itself failing
        _mock_status(remaining="lots"),  # unexpected body
    ],
)
def test_check_email_domain_alerts_when_rate_limited_without_known_credits(status_conn):
    with (
        patch(
            HTTPS_CONNECTION,
            side_effect=[_mock_connection(429), _mock_connection(429), status_conn],
        ),
        patch(SLEEP),
        patch(PUSHOVER) as mock_pushover,
    ):
        assert check_email_domain("x@example.org", "example.org") is None

    mock_pushover.assert_called_once()


def test_check_email_domain_alerts_when_status_lookup_errors():
    with (
        patch(
            HTTPS_CONNECTION,
            side_effect=[_mock_connection(429), _mock_connection(429), OSError("unreachable")],
        ),
        patch(SLEEP),
        patch(PUSHOVER) as mock_pushover,
    ):
        assert check_email_domain("x@example.org", "example.org") is None

    mock_pushover.assert_called_once()


def test_check_email_domain_caches_credit_status():
    with (
        patch(
            HTTPS_CONNECTION,
            side_effect=[
                _mock_connection(429),
                _mock_connection(429),
                _mock_status(remaining=500),
                # The second lookup reuses the cached credit status: no /status call.
                _mock_connection(429),
                _mock_connection(429),
            ],
        ) as mock_conn,
        patch(SLEEP),
    ):
        assert check_email_domain("x@example.org", "example.org") == {"rate_limited": True}
        assert check_email_domain("y@example.net", "example.net") == {"rate_limited": True}

    assert mock_conn.call_count == 5


def test_check_email_domain_alerts_at_most_once_per_interval():
    with (
        patch(HTTPS_CONNECTION, side_effect=lambda *a, **kw: _mock_connection(500)),
        patch(PUSHOVER) as mock_pushover,
    ):
        assert check_email_domain("x@example.org", "example.org") is None
        assert check_email_domain("y@example.net", "example.net") is None

    mock_pushover.assert_called_once()


def test_check_email_domain_returns_none_on_network_error():
    conn = _mock_connection()
    conn.request.side_effect = TimeoutError("timed out")
    with patch(HTTPS_CONNECTION, return_value=conn), patch(PUSHOVER) as mock_pushover:
        assert check_email_domain("x@example.org", "example.org") is None
    conn.close.assert_called_once()
    mock_pushover.assert_called_once()


def test_check_email_domain_returns_none_when_connection_fails():
    with patch(HTTPS_CONNECTION, side_effect=OSError("unreachable")):
        assert check_email_domain("x@example.org", "example.org") is None


def test_check_email_domain_skips_lookup_without_api_key(settings):
    settings.USERCHECK_API_KEY = ""
    with patch(HTTPS_CONNECTION) as mock_conn, patch(PUSHOVER) as mock_pushover:
        assert check_email_domain("x@example.org", "example.org") is None
    mock_conn.assert_not_called()
    mock_pushover.assert_not_called()


def test_check_email_domain_fails_open_when_alert_fails():
    with (
        patch(HTTPS_CONNECTION, side_effect=OSError("unreachable")),
        patch(PUSHOVER, side_effect=OSError("pushover unreachable")) as mock_pushover,
    ):
        assert check_email_domain("x@example.org", "example.org") is None
    mock_pushover.assert_called_once()


@pytest.mark.parametrize("body", [[], None, "ok"])
def test_check_email_domain_returns_none_on_unexpected_response_shape(body):
    conn = _mock_connection()
    conn.getresponse.side_effect = None
    conn.getresponse.return_value.status = 200
    conn.getresponse.return_value.read.return_value = json.dumps(body).encode()
    with patch(HTTPS_CONNECTION, return_value=conn), patch(PUSHOVER) as mock_pushover:
        assert check_email_domain("x@example.org", "example.org") is None
    mock_pushover.assert_called_once()


def test_check_email_domain_ignores_non_string_suggestion():
    body = {**USERCHECK_BODY, "did_you_mean": {"email": "x@gmail.com"}}
    with patch(HTTPS_CONNECTION, return_value=_mock_connection(body=body)):
        assert check_email_domain("x@example.org", "example.org")["suggested_domain"] is None
