"""Tests for metron.utils.get_recaptcha_auth (hCaptcha verification)."""

import io
import urllib.error
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from metron.utils import HCAPTCHA_TIMEOUT, HCAPTCHA_UNAVAILABLE, get_recaptcha_auth

URLOPEN = "metron.utils.urllib.request.urlopen"


@pytest.fixture
def captcha_request():
    return RequestFactory().post("/accounts/signup/", {"h-captcha-response": "token"})


def test_returns_hcaptcha_result_and_sets_timeout(captcha_request):
    body = io.BytesIO(b'{"success": true}')
    with patch(URLOPEN, return_value=body) as mock_urlopen:
        result = get_recaptcha_auth(captcha_request)

    assert result == {"success": True}
    assert mock_urlopen.call_args.kwargs["timeout"] == HCAPTCHA_TIMEOUT


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("timed out"),
        ConnectionResetError("reset by peer"),
        urllib.error.URLError("connection refused"),
    ],
)
def test_network_failure_reports_unavailable(captcha_request, error):
    with patch(URLOPEN, side_effect=error):
        result = get_recaptcha_auth(captcha_request)

    assert result == {"success": False, "error-codes": [HCAPTCHA_UNAVAILABLE]}


def test_unparseable_response_reports_unavailable(captcha_request):
    with patch(URLOPEN, return_value=io.BytesIO(b"<html>Bad Gateway</html>")):
        result = get_recaptcha_auth(captcha_request)

    assert result == {"success": False, "error-codes": [HCAPTCHA_UNAVAILABLE]}
