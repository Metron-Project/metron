"""Tests for users.forms.validate_email_allowed, shared by signup and email changes."""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from users.forms import validate_email_allowed

CHECK = "users.forms.check_email_domain"
CLEAN = {
    "disposable": False,
    "spam": False,
    "relay_domain": False,
    "mx": True,
    "suggested_domain": None,
}

pytestmark = pytest.mark.django_db


def _error(email, verdict=CLEAN):
    with patch(CHECK, return_value=verdict) as mock_check:
        try:
            validate_email_allowed(email)
        except ValidationError as exc:
            return exc.messages[0], mock_check
    return None, mock_check


@pytest.mark.parametrize(
    "email",
    [
        "x@mailinator.com",  # disposable-email-domains package
        "x@inbox.mailinator.com",  # subdomain of a package-listed domain
        "x@duck.com",  # hand-kept blocklist
        "x@Duck.COM",
    ],
)
def test_local_blocklists_reject_without_lookup(email):
    message, mock_check = _error(email)
    assert message == "Temporary email addresses are not allowed."
    mock_check.assert_not_called()


def test_allowlisted_domain_skips_lookup():
    message, mock_check = _error("x@Gmail.com")
    assert message is None
    mock_check.assert_not_called()


def test_clean_verdict_is_allowed():
    message, mock_check = _error("x@example.org")
    assert message is None
    mock_check.assert_called_once_with("x@example.org", "example.org")


def test_lookup_gets_normalized_domain():
    message, mock_check = _error("x@Example.ORG")
    assert message is None
    mock_check.assert_called_once_with("x@Example.ORG", "example.org")


def test_fails_open_without_verdict():
    message, _mock = _error("x@example.org", verdict=None)
    assert message is None


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"disposable": True}, "Temporary email addresses are not allowed."),
        ({"spam": True}, "Temporary email addresses are not allowed."),
        ({"relay_domain": True}, "Email forwarding addresses are not allowed."),
        ({"mx": False}, "Email address is not valid."),
        ({"mx": False, "suggested_domain": "gmail.com"}, "Did you mean x@gmail.com?"),
        # An unknown MX result isn't grounds to reject.
        ({"mx": None}, None),
        # A suggestion alone doesn't block an address that can receive mail.
        ({"suggested_domain": "gmail.com"}, None),
    ],
)
def test_verdict_mapping(overrides, expected):
    message, _mock = _error("x@example.org", verdict={**CLEAN, **overrides})
    assert message == expected


def test_malformed_address_is_rejected():
    message, _mock = _error("x@example.org", verdict={"invalid": True})
    assert message == "Email address is not valid."


def test_rate_limited_lookup_asks_user_to_retry():
    message, _mock = _error("x@example.org", verdict={"rate_limited": True})
    assert message == (
        "We couldn't verify your email address right now. Please try again in a moment."
    )


def test_address_without_domain_is_rejected():
    message, mock_check = _error("no-at-sign")
    assert message == "Email address is not valid."
    mock_check.assert_not_called()
