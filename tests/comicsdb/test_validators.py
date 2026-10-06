from datetime import date

import pytest
from django.core.exceptions import ValidationError

from comicsdb.validators import clean_upc, validate_upc

MODERN = date(2020, 1, 1)
LEGACY = date(1976, 7, 1)


@pytest.mark.parametrize(
    "upc",
    [
        "123456789012",
        "9780930655273",
        "12345678901201",
        "978093065527301",
        "76194137738400111",
        "978093065527300111",
    ],
    ids=["upc_a", "ean_13", "upc_a_2_addon", "ean_13_2_addon", "upc_a_5_addon", "ean_13_5_addon"],
)
def test_validate_upc_valid(upc):
    validate_upc(upc, MODERN)


@pytest.mark.parametrize(
    ("upc", "code"),
    [
        ("UPC 123", "upc_not_numeric"),
        ("1234-5678-9012", "upc_not_numeric"),
        ("\uff11" * 12, "upc_not_numeric"),
        ("12345678901", "upc_invalid_length"),
        ("1234567890123456", "upc_invalid_length"),
        ("1234567890123456789", "upc_invalid_length"),
        ("123456789013", "upc_invalid_check_digit"),
        ("9780930655274", "upc_invalid_check_digit"),
        ("12345678901301", "upc_invalid_check_digit"),
        ("978093065527401", "upc_invalid_check_digit"),
        ("76194137738500111", "upc_invalid_check_digit"),
        ("978093065527400111", "upc_invalid_check_digit"),
    ],
    ids=[
        "spaces",
        "hyphens",
        "fullwidth_digits",
        "11_digits",
        "16_digits",
        "19_digits",
        "bad_check_upc_a",
        "bad_check_ean_13",
        "bad_check_upc_a_2_addon",
        "bad_check_ean_13_2_addon",
        "bad_check_upc_a_5_addon",
        "bad_check_ean_13_5_addon",
    ],
)
def test_validate_upc_invalid(upc, code):
    with pytest.raises(ValidationError) as exc_info:
        validate_upc(upc, MODERN)
    assert exc_info.value.code == code


def test_validate_upc_legacy_13_digit_skips_check_digit():
    # Printed on Fantastic Four #172 (July 1976) without a check digit.
    validate_upc("0714860246207", LEGACY)


@pytest.mark.parametrize(
    ("upc", "cover_date", "code"),
    [
        ("0714860246207", date(1993, 1, 1), "upc_invalid_check_digit"),
        ("12345678901301", LEGACY, "upc_invalid_check_digit"),
        ("071486024620", LEGACY, None),
        ("07148602462", LEGACY, "upc_invalid_length"),
    ],
    ids=["13_digit_from_legacy_cutoff", "legacy_14_digit", "legacy_upc_a", "legacy_11_digit"],
)
def test_validate_upc_legacy_rule_only_covers_13_digit(upc, cover_date, code):
    if code is None:
        validate_upc(upc, cover_date)
        return
    with pytest.raises(ValidationError) as exc_info:
        validate_upc(upc, cover_date)
    assert exc_info.value.code == code


def test_clean_upc_raises_keyed_on_upc():
    with pytest.raises(ValidationError) as exc_info:
        clean_upc("123456789013", MODERN)
    assert exc_info.value.message_dict == {"upc": ["UPC check digit is invalid."]}


@pytest.mark.parametrize(
    ("upc", "cover_date"),
    [("", MODERN), ("123456789013", None), ("UPC 123", MODERN), ("0714860246207", LEGACY)],
    ids=["no_upc", "no_cover_date", "bad_format_left_to_field_validator", "legacy"],
)
def test_clean_upc_skips(upc, cover_date):
    clean_upc(upc, cover_date)
