from datetime import date

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Valid UPC lengths mapped to the length of their base (UPC-A or EAN-13) code. Anything
# after the base is a 2 or 5 digit add-on, which has no check digit. A 14 digit value is
# treated as UPC-A plus a 2 digit add-on, not a GTIN-14, since comic barcodes use add-ons.
UPC_BASE_LENGTHS = {12: 12, 13: 13, 14: 12, 15: 13, 17: 12, 18: 13}

# Comics from before this year may carry a 13 digit barcode that is printed without a check
# digit: an 11 digit UPC-A body followed by a 2 digit cover month, e.g. '07148602462' + '07'.
LEGACY_UPC_YEAR = 1993
LEGACY_UPC_LENGTH = 13


def upc_check_digit(body: str) -> str:
    """Return the GS1 mod-10 check digit for a UPC-A/EAN-13 code missing its last digit."""
    total = sum(int(d) * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(body)))
    return str((10 - total % 10) % 10)


def upc_check_digit_valid(code: str) -> bool:
    """Return True if the last digit of a UPC-A/EAN-13 code is a valid GS1 mod-10 check digit."""
    return upc_check_digit(code[:-1]) == code[-1]


def validate_upc_format(value: str) -> None:
    """Validate that a UPC is numeric and has the length of a UPC-A or EAN-13 code, optionally
    followed by a 2 or 5 digit add-on."""
    # isascii() rules out non-ASCII digits (e.g. "²" or fullwidth digits) that isdigit() allows.
    if not (value.isascii() and value.isdigit()):
        raise ValidationError(
            _("UPC must be numeric. No spaces or hyphens allowed."), code="upc_not_numeric"
        )
    if len(value) not in UPC_BASE_LENGTHS:
        raise ValidationError(
            _("UPC must be 12 or 13 digits, optionally followed by a 2 or 5 digit add-on."),
            code="upc_invalid_length",
        )


def validate_upc_check_digit(value: str, cover_date: date) -> None:
    """Validate the check digit of a UPC that has passed `validate_upc_format`, skipping
    legacy barcodes that were printed without one."""
    if len(value) == LEGACY_UPC_LENGTH and cover_date.year < LEGACY_UPC_YEAR:
        return
    if not upc_check_digit_valid(value[: UPC_BASE_LENGTHS[len(value)]]):
        raise ValidationError(_("UPC check digit is invalid."), code="upc_invalid_check_digit")


def validate_upc(value: str, cover_date: date) -> None:
    """Validate a UPC's format and check digit for an issue with the given cover date."""
    validate_upc_format(value)
    validate_upc_check_digit(value, cover_date)


def clean_upc(upc: str, cover_date: date | None) -> None:
    """
    Model `clean()` helper: validate a UPC's check digit against its issue's cover date.

    Does nothing when there is no UPC or cover date, or when the UPC fails
    `validate_upc_format`, since the field validator already reports that error.

    Raises:
        ValidationError: Keyed on the `upc` field if the check digit is invalid.
    """
    if not (upc and cover_date):
        return
    try:
        validate_upc_format(upc)
    except ValidationError:
        return
    try:
        validate_upc_check_digit(upc, cover_date)
    except ValidationError as exc:
        raise ValidationError({"upc": exc}) from exc
