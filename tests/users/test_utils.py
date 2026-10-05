"""Tests for users.utils helpers."""

import json
from unittest.mock import MagicMock, patch

import pytest

from users.utils import check_email_domain

HTTPS_CONNECTION = "users.utils.http.client.HTTPSConnection"


def _mock_connection(status=200, body=None):
    conn = MagicMock()
    response = conn.getresponse.return_value
    response.status = status
    response.reason = "OK" if status == 200 else "Error"
    response.read.return_value = json.dumps(body or {"block": False}).encode()
    return conn


@pytest.mark.parametrize(
    ("email", "expected_query"),
    [
        ("someone@example.org", "domain=someone%40example.org"),
        # A quoted local part may contain characters that are special in a query.
        ('"a&b=c#d"@example.org', "domain=%22a%26b%3Dc%23d%22%40example.org"),
        ('"first last"@example.org', "domain=%22first+last%22%40example.org"),
    ],
)
def test_check_email_domain_encodes_query(email, expected_query):
    conn = _mock_connection()
    with patch(HTTPS_CONNECTION, return_value=conn):
        check_email_domain(email)

    method, path = conn.request.call_args.args
    assert method == "GET"
    assert path == f"/?{expected_query}"


def test_check_email_domain_returns_parsed_response():
    body = {"block": True, "disposable": True}
    with patch(HTTPS_CONNECTION, return_value=_mock_connection(body=body)):
        assert check_email_domain("x@example.org") == body


def test_check_email_domain_returns_none_on_error_status():
    with patch(HTTPS_CONNECTION, return_value=_mock_connection(status=500)):
        assert check_email_domain("x@example.org") is None


def test_check_email_domain_returns_none_on_network_error():
    conn = _mock_connection()
    conn.request.side_effect = TimeoutError("timed out")
    with patch(HTTPS_CONNECTION, return_value=conn):
        assert check_email_domain("x@example.org") is None
    conn.close.assert_called_once()
