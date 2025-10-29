from typing import TYPE_CHECKING

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from comicsdb.models import Issue, Series, Universe
from users.models import CustomUser

if TYPE_CHECKING:
    from django.db.models import QuerySet


class Command(BaseCommand):
    help = "Add Universe to Series Issues"

    def add_arguments(self, parser):
        """
        Add command line arguments for the add_universe_to_series management command.

        Args:
            parser: The parser object to which the arguments are added.

        Returns:
            None
        """
        parser.add_argument("--series", type=int, required=True, help="Series ID number")
        parser.add_argument("--universe", type=int, required=True, help="Universe ID number")
        parser.add_argument("--characters", action="store_true", help="Add characters to Universe.")

    def handle(self, *args, **options):
        """
        Add a universe to all issues in a series and optionally to all characters in those issues.

        Args:
            *args: Variable length argument list.
            **options: Keyword arguments containing series, universe, and characters flags.

        Returns:
            None

        Raises:
            CommandError: If series or universe does not exist.
        """
        # Validate inputs
        try:
            series = Series.objects.get(pk=options["series"])
        except Series.DoesNotExist as exc:
            raise CommandError(f"Series with id {options['series']} does not exist") from exc

        try:
            universe = Universe.objects.get(pk=options["universe"])
        except Universe.DoesNotExist as exc:
            raise CommandError(f"Universe with id {options['universe']} does not exist") from exc

        system_user = CustomUser.objects.get(id=1)

        # Initialize counters
        issues_updated = 0
        characters_updated = 0
        processed_characters = set()

        self.stdout.write(f"Adding universe '{universe}' to series '{series}'...")

        with transaction.atomic():
            issues: QuerySet[Issue] = Issue.objects.filter(series=series).prefetch_related(
                "universes", "characters__universes"
            )

            if not issues.exists():
                self.stdout.write(self.style.WARNING(f"No issues found for series '{series}'"))
                return

            for issue in issues:
                # Check if universe is already associated with this issue
                if not issue.universes.filter(pk=universe.pk).exists():
                    issue.universes.add(universe)
                    issue.edited_by = system_user
                    issue._change_reason = f"Added universe '{universe}' via management command"
                    issue.save()
                    issues_updated += 1
                    self.stdout.write(self.style.SUCCESS(f"Added '{universe}' to '{issue}'"))

                # Process characters if requested
                if options["characters"]:
                    for character in issue.characters.all():
                        # Skip if we've already processed this character
                        if character.pk in processed_characters:
                            continue

                        # Check if universe is already associated with this character
                        if not character.universes.filter(pk=universe.pk).exists():
                            character.universes.add(universe)
                            character.edited_by = system_user
                            character._change_reason = (
                                f"Added universe '{universe}' via management command"
                            )
                            character.save()
                            characters_updated += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"Added '{universe}' to '{character}'")
                            )

                        # Mark as processed
                        processed_characters.add(character.pk)

        # Print summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nSummary: Updated {issues_updated} issue(s) and "
                f"{characters_updated} character(s)"
            )
        )
