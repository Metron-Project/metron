import pytest
from django.core.exceptions import ValidationError

from comicsdb.validators import validate_upc


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
    validate_upc(upc)


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
        validate_upc(upc)
    assert exc_info.value.code == code
