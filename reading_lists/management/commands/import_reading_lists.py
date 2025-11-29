"""
Management command to import reading lists from JSON files.

Expected JSON format:
{
  "name": "Reading List Name",
  "source": "LoCG",  # Attribution source code
  "books": [
    {"index": 0, "database": {"id": 123}},
    {"index": 1, "database": {"id": 456}},
    ...
  ]
}
"""

import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from comicsdb.models.issue import Issue
from reading_lists.models import ReadingList, ReadingListItem
from users.models import CustomUser


class Command(BaseCommand):
    help = "Import reading lists from JSON files, assigning ownership to the Metron user"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "paths",
            nargs="+",
            type=str,
            help="Path(s) to JSON file(s) or directory containing JSON files",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate import without making changes",
        )
        parser.add_argument(
            "--skip-missing",
            action="store_true",
            help="Skip issues that don't exist in the database instead of failing",
        )

    def handle(self, *args, **options) -> None:  # noqa: PLR0912
        dry_run = options["dry_run"]
        skip_missing = options["skip_missing"]

        # Get the Metron user
        try:
            metron_user = CustomUser.objects.get(username="Metron")
        except CustomUser.DoesNotExist as err:
            msg = 'User "Metron" does not exist. Please create this user first.'
            raise CommandError(msg) from err

        # Collect all JSON files from provided paths
        json_files = []
        for path_str in options["paths"]:
            path = Path(path_str)
            if not path.exists():
                raise CommandError(f"Path does not exist: {path}")

            if path.is_file():
                if path.suffix == ".json":
                    json_files.append(path)
                else:
                    self.stdout.write(self.style.WARNING(f"Skipping non-JSON file: {path}"))
            elif path.is_dir():
                json_files.extend(path.glob("*.json"))
            else:
                raise CommandError(f"Invalid path: {path}")

        if not json_files:
            raise CommandError("No JSON files found to import")

        self.stdout.write(self.style.SUCCESS(f"Found {len(json_files)} JSON file(s) to import"))

        # Import each file
        created_count = 0
        skipped_count = 0
        error_count = 0

        for json_file in json_files:
            try:
                result = self._import_reading_list(json_file, metron_user, dry_run, skip_missing)
                if result == "created":
                    created_count += 1
                elif result == "skipped":
                    skipped_count += 1
            except (CommandError, ValueError, KeyError) as e:
                error_count += 1
                self.stdout.write(self.style.ERROR(f"Error importing {json_file.name}: {e}"))

        # Print summary
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 50))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed: {created_count} reading list(s)")
        )
        if skipped_count > 0:
            self.stdout.write(
                self.style.WARNING(f"Skipped (already exists): {skipped_count} reading list(s)")
            )
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count} reading list(s)"))

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """Remove year prefixes from reading list names.

        Examples:
            "[2015-2016] Justice League" -> "Justice League"
            "[2015] Crisis" -> "Crisis"
            "(2015-2016) Justice League" -> "Justice League"
            "Justice League" -> "Justice League"
        """
        # Remove patterns like [YYYY-YYYY], [YYYY], (YYYY-YYYY), (YYYY) from the beginning
        pattern = r"^[\[\(]\d{4}(?:-\d{4})?[\]\)]\s*"
        return re.sub(pattern, "", name).strip()

    def _import_reading_list(
        self, json_file: Path, metron_user: CustomUser, dry_run: bool, skip_missing: bool
    ) -> str:
        """Import a single reading list from a JSON file.

        Returns:
            "created" if the list was created
            "skipped" if the list already exists
        """
        self.stdout.write(f"\nProcessing: {json_file.name}")

        # Parse JSON file
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON in {json_file.name}: {e}") from e

        # Validate required fields
        if "name" not in data:
            raise CommandError(f"Missing 'name' field in {json_file.name}")
        if "books" not in data:
            raise CommandError(f"Missing 'books' field in {json_file.name}")

        list_name = self._sanitize_name(data["name"])
        source = data.get("source", "")
        books = data["books"]

        # Map source code to attribution_source
        source_mapping = {
            "CBRO": ReadingList.AttributionSource.CBRO,
            "CMRO": ReadingList.AttributionSource.CMRO,
            "CBH": ReadingList.AttributionSource.CBH,
            "CBT": ReadingList.AttributionSource.CBT,
            "MG": ReadingList.AttributionSource.MG,
            "HTLC": ReadingList.AttributionSource.HTLC,
            "LoCG": ReadingList.AttributionSource.LOCG,
            "LOCG": ReadingList.AttributionSource.LOCG,
            "OTHER": ReadingList.AttributionSource.OTHER,
        }
        attribution_source = source_mapping.get(source, "")

        # Check if reading list already exists
        if ReadingList.objects.filter(user=metron_user, name=list_name).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"  Reading list '{list_name}' already exists for user Metron - skipping"
                )
            )
            return "skipped"

        # Validate all issues exist before creating the reading list
        issue_ids = [book["database"]["id"] for book in books]
        existing_issues = Issue.objects.filter(id__in=issue_ids)
        existing_issue_ids = set(existing_issues.values_list("id", flat=True))

        missing_ids = set(issue_ids) - existing_issue_ids
        if missing_ids:
            if skip_missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Warning: {len(missing_ids)} issue(s) not found: {sorted(missing_ids)}"
                    )
                )
            else:
                raise CommandError(
                    f"Issues not found in database: {sorted(missing_ids)}. "
                    "Use --skip-missing to continue anyway."
                )

        if dry_run:
            issue_count = len([b for b in books if b["database"]["id"] in existing_issue_ids])
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Would create reading list: {list_name} with {issue_count} issue(s)"
                )
            )
            if attribution_source:
                self.stdout.write(self.style.SUCCESS(f"  Attribution source: {attribution_source}"))
            return "created"

        # Create the reading list and items in a transaction
        with transaction.atomic():
            reading_list = ReadingList.objects.create(
                user=metron_user,
                name=list_name,
                attribution_source=attribution_source,
                is_private=False,
            )

            # Create reading list items using bulk_create for better performance
            items_to_create = [
                ReadingListItem(
                    reading_list=reading_list,
                    issue_id=book["database"]["id"],
                    order=book["index"],
                )
                for book in books
                if book["database"]["id"] in existing_issue_ids
            ]

            ReadingListItem.objects.bulk_create(items_to_create)
            items_created = len(items_to_create)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created reading list: {list_name} with {items_created} issue(s)"
                )
            )
            if attribution_source:
                source_label = ReadingList.AttributionSource(attribution_source).label
                self.stdout.write(self.style.SUCCESS(f"  Attribution source: {source_label}"))

        return "created"
