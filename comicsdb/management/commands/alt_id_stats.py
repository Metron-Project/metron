from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from comicsdb.models.issue import Issue


class Command(BaseCommand):
    help = "Print Alternative ID statistics."

    def handle(self, *args: any, **options: any) -> None:
        stats = Issue.objects.aggregate(
            total=Count("id"),
            cv_missing=Count("id", filter=Q(cv_id__isnull=True)),
            gcd_missing=Count("id", filter=Q(gcd_id__isnull=True)),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Missing CV ID: {stats['cv_missing']}\n"
                f"With CV ID: {stats['total'] - stats['cv_missing']}\n"
                f"Total Issues: {stats['total']}\n"
                f"Missing CV Percentage: {stats['cv_missing'] / stats['total']:.2%}\n\n"
                f"Missing GCD ID: {stats['gcd_missing']}\n"
                f"With GCD ID: {stats['total'] - stats['gcd_missing']}\n"
                f"Total Issues: {stats['total']}\n"
                f"Missing GCD Percentage: {stats['gcd_missing'] / stats['total']:.2%}"
            )
        )
