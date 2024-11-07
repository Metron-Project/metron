from django.core.management import BaseCommand
from django.db.models import Count

from comicsdb.models import Publisher, Series


class Command(BaseCommand):
    help = "Find possible bad Series volumes"

    def handle(self, *args, **options):
        # Check for Limited Series (11), One-Shots (5), or Single Issues (13)
        #
        # Exclude Annual (6), Digital Chapter (12), Graphic Novel (9), Hardcover (8), Omnibus (15) and
        # Trade Paperbacks (10)
        excluded_series_types = [6, 12, 9, 8, 15, 10]

        pubs = Publisher.objects.only("id", "name").all()
        for pub in pubs:
            self.stdout.write(
                self.style.WARNING(f"Searching '{pub}' for possible bad volumes")
            )

            if qs := list(
                Series.objects.filter(publisher=pub)
                .exclude(series_type__in=excluded_series_types)
                .values("name", "volume")
                .annotate(volume_count=Count("volume"))
                .filter(volume_count__gt=1)
                .order_by("name")
            ):
                for i in qs:
                    self.stdout.write(self.style.SUCCESS(f"{i['name']} - {i['volume_count']}"))
            else:
                self.stdout.write(self.style.SUCCESS(f"No bad volumes found for '{pub}'"))
