from datetime import datetime

from django.core.management.base import BaseCommand
from django.db.models import Q

from comicsdb.models import Arc, Character, Creator, Issue, Publisher, Series, Team
from users.models import CustomUser


class Command(BaseCommand):
    help = "Show created / modified objects"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date", type=str, required=True, help="Date string to search (yyyy-mm-dd)"
        )

    def handle(self, *args, **options):
        search_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
        admin = CustomUser.objects.get(id=1)

        models = [Arc, Issue, Character, Creator, Series, Team, Publisher]
        results = []

        for mod in models:
            if qs := mod.objects.filter(
                Q(modified__date=search_date) & ~Q(created_by=admin) & ~Q(edited_by=admin)
            ).distinct():
                results.append({"model": mod, "qs": qs})

        if not results:
            self.stdout.write(self.style.WARNING("No changes found."))
            return

        title = f"Changes for {search_date}\n-----------------------"
        self.stdout.write(self.style.SUCCESS(title))

        for item in results:
            self.stdout.write(self.style.SUCCESS(f"\n{item['model'].__name__}:"))
            for obj in item["qs"]:
                user_str = obj.edited_by or obj.created_by
                self.stdout.write(self.style.WARNING(f"\t'{obj}' created/changed by '{user_str}'"))
