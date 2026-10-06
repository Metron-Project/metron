from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Valid UPC lengths mapped to the length of their base (UPC-A or EAN-13) code. Anything
# after the base is a 2 or 5 digit add-on, which has no check digit.
UPC_BASE_LENGTHS = {12: 12, 13: 13, 14: 12, 15: 13, 17: 12, 18: 13}


def upc_check_digit_valid(code: str) -> bool:
    """Return True if the last digit of a UPC-A/EAN-13 code is a valid GS1 mod-10 check digit."""
    *body, check = (int(c) for c in code)
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return (10 - total % 10) % 10 == check


def validate_upc(value: str) -> None:
    """Validate a UPC-A or EAN-13 code, optionally followed by a 2 or 5 digit add-on."""
    # isascii() rules out non-ASCII digits (e.g. "²" or fullwidth digits) that isdigit() allows.
    if not (value.isascii() and value.isdigit()):
        raise ValidationError(
            _("UPC must be numeric. No spaces or hyphens allowed."), code="upc_not_numeric"
        )
    base_length = UPC_BASE_LENGTHS.get(len(value))
    if base_length is None:
        raise ValidationError(
            _("UPC must be 12 or 13 digits, optionally followed by a 2 or 5 digit add-on."),
            code="upc_invalid_length",
        )
    if not upc_check_digit_valid(value[:base_length]):
        raise ValidationError(_("UPC check digit is invalid."), code="upc_invalid_check_digit")
