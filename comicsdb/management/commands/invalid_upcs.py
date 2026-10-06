import json
from collections import Counter
from datetime import date
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from comicsdb.models import Issue, Variant
from comicsdb.validators import LEGACY_UPC_YEAR, upc_check_digit, validate_upc
from users.models import CustomUser

MARVEL_MANUFACTURER_CODE = "59606"


def upc_error_code(upc: str, cover_date: date) -> str | None:
    """Return the validation error code for an invalid UPC, or None if it's valid."""
    try:
        validate_upc(upc, cover_date)
    except ValidationError as exc:
        return exc.code
    return None


def repair_upc(upc: str, cover_date: date) -> str | None:
    """
    Rebuild a valid UPC from a known, systematically mis-entered format.

    Recognized formats, each confirmed against cover images:

    - 12 digits on a legacy issue, ending in its cover month: a legacy 13 digit UPC
      without its leading '0', e.g. '709893071712' -> '0709893071712'.
    - 15 digits starting with Marvel's manufacturer code: a UPC-A plus 5 digit add-on
      without the leading number system digit '7' or the check digit.
    - 16 digits: a UPC-A plus 5 digit add-on without the check digit.
    - 18 digits starting with Marvel's '7' + manufacturer code: a UPC-A plus 5 digit
      add-on with a stray digit before the check digit, e.g. '75960609268' + '1' +
      '003111' -> '75960609268003111'.

    Args:
        upc: The invalid UPC.
        cover_date: The cover date of the issue the UPC belongs to.

    Returns:
        The repaired UPC, or None if the UPC isn't in a recognized format or the repaired
        value still fails validation.
    """
    if not (upc.isascii() and upc.isdigit()):
        return None
    match len(upc):
        case 12 if cover_date.year < LEGACY_UPC_YEAR and int(upc[-2:]) == cover_date.month:
            repaired = "0" + upc
        case 15 if upc.startswith(MARVEL_MANUFACTURER_CODE):
            base = "7" + upc[:10]
            repaired = base + upc_check_digit(base) + upc[10:]
        case 16:
            repaired = upc[:11] + upc_check_digit(upc[:11]) + upc[11:]
        case 18 if upc.startswith("7" + MARVEL_MANUFACTURER_CODE):
            repaired = upc[:11] + upc[12:]
        case _:
            return None
    return repaired if upc_error_code(repaired, cover_date) is None else None


class Command(BaseCommand):
    help = "Export (and optionally repair or clear) Issue and Variant UPCs that fail validation"

    def add_arguments(self, parser):
        """
        Add command line arguments for the invalid_upcs management command.

        Args:
            parser: The parser object to which the arguments are added.

        Returns:
            None
        """
        parser.add_argument(
            "--output", type=Path, required=True, help="JSON file to export the invalid UPCs to."
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help=(
                "Repair the invalid UPCs in a recognized format and blank the rest. Without "
                "this the command only exports and reports."
            ),
        )

    def handle(self, *args, **options):
        """
        Find every Issue and Variant with an invalid UPC, write them to a JSON file, and
        optionally repair or clear the invalid values.

        Args:
            *args: Variable length argument list.
            **options: Keyword arguments containing the output path and clear flag.

        Returns:
            None
        """
        bad_issues: list[tuple[Issue, str, str | None]] = []
        for issue in (
            Issue.objects.exclude(upc="").select_related("series").order_by("pk").iterator()
        ):
            if reason := upc_error_code(issue.upc, issue.cover_date):
                bad_issues.append((issue, reason, repair_upc(issue.upc, issue.cover_date)))

        bad_variants: list[tuple[Variant, str, str | None]] = []
        for variant in (
            Variant.objects.exclude(upc="").select_related("issue").order_by("pk").iterator()
        ):
            if reason := upc_error_code(variant.upc, variant.issue.cover_date):
                bad_variants.append(
                    (variant, reason, repair_upc(variant.upc, variant.issue.cover_date))
                )

        export = {
            "generated": timezone.now().isoformat(),
            "issues": [
                {
                    "id": issue.pk,
                    "series_id": issue.series_id,
                    "series": str(issue.series),
                    "number": issue.number,
                    "cover_date": issue.cover_date.isoformat(),
                    "cv_id": issue.cv_id,
                    "gcd_id": issue.gcd_id,
                    "upc": issue.upc,
                    "reason": reason,
                    "repaired_upc": repaired,
                }
                for issue, reason, repaired in bad_issues
            ],
            "variants": [
                {
                    "id": variant.pk,
                    "issue_id": variant.issue_id,
                    "name": variant.name,
                    "upc": variant.upc,
                    "reason": reason,
                    "repaired_upc": repaired,
                }
                for variant, reason, repaired in bad_variants
            ],
        }
        output: Path = options["output"]
        output.write_text(json.dumps(export, indent=2))
        self.stdout.write(f"Exported invalid UPCs to '{output}'")

        for label, rows in (("issue", bad_issues), ("variant", bad_variants)):
            counts = Counter(reason for _, reason, _ in rows)
            repairable = sum(1 for *_, repaired in rows if repaired)
            self.stdout.write(f"Invalid {label} UPCs: {len(rows)} ({repairable} repairable)")
            for reason, count in sorted(counts.items()):
                self.stdout.write(f"  {reason}: {count}")

        if not options["clear"]:
            self.stdout.write(
                self.style.WARNING("Dry run: no UPCs were repaired or cleared (use --clear).")
            )
            return

        repaired_count, cleared_count = self._fix_upcs(
            [issue.pk for issue, *_ in bad_issues], [variant.pk for variant, *_ in bad_variants]
        )
        self.stdout.write(
            self.style.SUCCESS(f"Repaired {repaired_count} UPC(s) and cleared {cleared_count}")
        )

    @staticmethod
    def _fix_upcs(issue_ids: list[int], variant_ids: list[int]) -> tuple[int, int]:
        """
        Repair or clear the invalid UPCs of the given issues and variants.

        Args:
            issue_ids: Primary keys of the issues with an invalid UPC.
            variant_ids: Primary keys of the variants with an invalid UPC.

        Returns:
            The number of UPCs repaired and the number cleared.
        """
        system_user = CustomUser.objects.get(id=1)
        repaired_count = cleared_count = 0

        with transaction.atomic():
            # Re-fetch and lock the rows so an edit made since the scan isn't overwritten
            # with stale values, and skip any UPC that has been fixed in the meantime.
            locked_issues = Issue.objects.select_for_update().filter(pk__in=issue_ids)
            for issue in locked_issues:
                if not (reason := upc_error_code(issue.upc, issue.cover_date)):
                    continue
                if repaired := repair_upc(issue.upc, issue.cover_date):
                    issue._change_reason = f"Repaired UPC '{issue.upc}' ({reason})"
                    repaired_count += 1
                else:
                    issue._change_reason = f"Cleared invalid UPC '{issue.upc}' ({reason})"
                    cleared_count += 1
                issue.upc = repaired or ""
                issue.edited_by = system_user
                issue.save(update_fields=["upc", "edited_by", "modified"])

            # Variant saves bump their issue's modified timestamp via a post_save signal.
            locked_variants = (
                Variant.objects.select_for_update(of=("self",))
                .select_related("issue")
                .filter(pk__in=variant_ids)
            )
            for variant in locked_variants:
                if not upc_error_code(variant.upc, variant.issue.cover_date):
                    continue
                if repaired := repair_upc(variant.upc, variant.issue.cover_date):
                    repaired_count += 1
                else:
                    cleared_count += 1
                variant.upc = repaired or ""
                variant.save(update_fields=["upc"])

        return repaired_count, cleared_count
