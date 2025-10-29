from datetime import date

from django.core.management.base import BaseCommand

from comicsdb.models import Character, Creator, Issue
from users.models import CustomUser


class Command(BaseCommand):
    help = "Get monthly stats"

    def add_arguments(self, parser) -> None:
        parser.add_argument("--month", type=int, required=True)
        parser.add_argument("--year", type=int, required=True)

    def handle(self, *args, **options) -> None:
        month = options["month"]
        year = options["year"]

        # Combine queries using annotation
        results = [
            {
                "model": CustomUser,
                "count": CustomUser.objects.filter(
                    date_joined__month=month, date_joined__year=year
                ).count(),
            }
        ]

        # Efficient counting for other models
        models = [Character, Creator, Issue]
        results.extend(
            {
                "model": mod,
                "count": mod.objects.filter(created_on__month=month, created_on__year=year).count(),
            }
            for mod in models
        )
        title = f"Stats for {date(year, month, 1).strftime('%B %Y')}"

        self.stdout.write(self.style.SUCCESS(title))
        self.stdout.write(self.style.SUCCESS(f"{'-' * len(title)}"))
        for result in results:
            self.stdout.write(
                self.style.WARNING(f"{result['model'].__name__}: {result['count']:,}")
            )
