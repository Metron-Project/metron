"""
One-time backfill: sync existing user_collection ratings into issue_ratings.

Populates issue_ratings.IssueRating from CollectionItem.rating values that were
set before the two apps were kept in sync via user_collection.signals.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from issue_ratings.models import IssueRating
from user_collection.models import CollectionItem


class Command(BaseCommand):
    help = "Backfill IssueRating rows from existing CollectionItem ratings."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would change without writing to the database",
        )

    def handle(self, *args, **options) -> None:
        dry_run = options["dry_run"]
        rated_items = CollectionItem.objects.filter(rating__isnull=False).select_related(
            "issue", "user"
        )

        created_count = 0
        updated_count = 0
        unchanged_count = 0

        with transaction.atomic():
            for item in rated_items.iterator():
                existing = IssueRating.objects.filter(issue=item.issue, user=item.user).first()

                if existing is None:
                    created_count += 1
                    IssueRating.objects.create(issue=item.issue, user=item.user, rating=item.rating)
                elif existing.rating != item.rating:
                    updated_count += 1
                    existing.rating = item.rating
                    existing.save(update_fields=["rating"])
                else:
                    unchanged_count += 1

            if dry_run:
                transaction.set_rollback(True)

        verb = "Would sync" if dry_run else "Synced"
        total = created_count + updated_count + unchanged_count
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {total} rated collection item(s): "
                f"{created_count} to create, {updated_count} to update, "
                f"{unchanged_count} already in sync."
            )
        )
