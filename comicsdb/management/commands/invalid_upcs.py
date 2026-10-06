import json
from collections import Counter
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from comicsdb.models import Issue, Variant
from comicsdb.validators import validate_upc
from users.models import CustomUser


def upc_error_code(upc: str) -> str | None:
    """Return the validation error code for an invalid UPC, or None if it's valid."""
    try:
        validate_upc(upc)
    except ValidationError as exc:
        return exc.code
    return None


class Command(BaseCommand):
    help = "Export (and optionally clear) Issue and Variant UPCs that fail validation"

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
            help="Blank the invalid UPCs. Without this the command only exports and reports.",
        )

    def handle(self, *args, **options):
        """
        Find every Issue and Variant with an invalid UPC, write them to a JSON file, and
        optionally clear the invalid values.

        Args:
            *args: Variable length argument list.
            **options: Keyword arguments containing the output path and clear flag.

        Returns:
            None
        """
        bad_issues: list[tuple[Issue, str]] = []
        for issue in (
            Issue.objects.exclude(upc="").select_related("series").order_by("pk").iterator()
        ):
            if reason := upc_error_code(issue.upc):
                bad_issues.append((issue, reason))

        bad_variants: list[tuple[Variant, str]] = []
        for variant in Variant.objects.exclude(upc="").order_by("pk").iterator():
            if reason := upc_error_code(variant.upc):
                bad_variants.append((variant, reason))

        export = {
            "generated": timezone.now().isoformat(),
            "issues": [
                {
                    "id": issue.pk,
                    "series_id": issue.series_id,
                    "series": str(issue.series),
                    "number": issue.number,
                    "cv_id": issue.cv_id,
                    "gcd_id": issue.gcd_id,
                    "upc": issue.upc,
                    "reason": reason,
                }
                for issue, reason in bad_issues
            ],
            "variants": [
                {
                    "id": variant.pk,
                    "issue_id": variant.issue_id,
                    "name": variant.name,
                    "upc": variant.upc,
                    "reason": reason,
                }
                for variant, reason in bad_variants
            ],
        }
        output: Path = options["output"]
        output.write_text(json.dumps(export, indent=2))
        self.stdout.write(f"Exported invalid UPCs to '{output}'")

        for label, rows in (("issue", bad_issues), ("variant", bad_variants)):
            counts = Counter(reason for _, reason in rows)
            self.stdout.write(f"Invalid {label} UPCs: {len(rows)}")
            for reason, count in sorted(counts.items()):
                self.stdout.write(f"  {reason}: {count}")

        if not options["clear"]:
            self.stdout.write(self.style.WARNING("Dry run: no UPCs were cleared (use --clear)."))
            return

        system_user = CustomUser.objects.get(id=1)

        with transaction.atomic():
            for issue, reason in bad_issues:
                issue._change_reason = f"Cleared invalid UPC '{issue.upc}' ({reason})"
                issue.upc = ""
                issue.edited_by = system_user
                issue.save()

            for variant, _ in bad_variants:
                variant.upc = ""
                variant.save(update_fields=["upc"])

            # Variants have no modified timestamp, so bump their issue's so API syncers
            # pick up the change.
            if variant_issue_ids := {variant.issue_id for variant, _ in bad_variants}:
                Issue.objects.filter(pk__in=variant_issue_ids).update(modified=timezone.now())

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared {len(bad_issues)} issue UPC(s) and {len(bad_variants)} variant UPC(s)"
            )
        )
