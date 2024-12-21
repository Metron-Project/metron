from django.core.management.base import BaseCommand, CommandParser

from comicsdb.models import Arc, Character, Creator, Issue, Publisher, Series, Team
from users.models import CustomUser


class Command(BaseCommand):
    help = "Get annual stats for all comics"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("year", type=int, help="Year for stats.")
        return super().add_arguments(parser)

    def handle(self, *args: any, **options: any) -> None:
        year = options["year"]

        # Aggregate counts in a single query
        results = {
            CustomUser: CustomUser.objects.filter(date_joined__year=year).count(),
            Arc: Arc.objects.filter(created_on__year=year).count(),
            Character: Character.objects.filter(created_on__year=year).count(),
            Creator: Creator.objects.filter(created_on__year=year).count(),
            Issue: Issue.objects.filter(created_on__year=year).count(),
            Publisher: Publisher.objects.filter(created_on__year=year).count(),
            Series: Series.objects.filter(created_on__year=year).count(),
            Team: Team.objects.filter(created_on__year=year).count(),
        }

        title = f"{year} New Additions Statistics"
        self.stdout.write(self.style.SUCCESS(f"{title}\n{len(title) * '-'}"))
        for model, count in results.items():
            self.stdout.write(self.style.WARNING(f"{model.__name__}: {count:,}"))
