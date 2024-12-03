from django.core.management import BaseCommand
from django.db.models import Count

from comicsdb.models import Publisher, Series, SeriesType


class Command(BaseCommand):
    help = "Find possible bad Series volumes"

    def handle(self, *args, **options):
        # Check for Limited Series (11), One-Shots (5), or Single Issues (13)
        #
        # Exclude Annual (6), Digital Chapter (12), Graphic Novel (9), Hardcover (8),
        # Omnibus (15) and Trade Paperbacks (10)
        excluded_series_types = {6, 12, 9, 8, 15, 10}

        pubs = Publisher.objects.only("id", "name").all()
        series_types_qs = SeriesType.objects.filter(pk__in=excluded_series_types).values_list(
            "id", "name"
        )

        # Pre-fetch all series data
        all_series = (
            Series.objects.exclude(series_type__in=excluded_series_types)
            .values("publisher_id", "name", "volume")
            .annotate(volume_count=Count("volume"))
            .filter(volume_count__gt=1)
            .order_by("name")
        )
        all_series_by_publisher = {}
        for series in all_series:
            all_series_by_publisher.setdefault(series["publisher_id"], []).append(series)

        for pub in pubs:
            if pub.id in all_series_by_publisher:
                for i in all_series_by_publisher[pub.id]:
                    self.stdout.write(
                        self.style.ERROR(
                            f"{i['name']} | {i['volume_count']} Duplicates | {pub} "
                        )
                    )

        # Pre-fetch all series data for excluded types
        all_excluded_series = (
            Series.objects.filter(series_type__in=excluded_series_types)
            .values("publisher_id", "series_type_id", "name", "volume")
            .annotate(volume_count=Count("volume"))
            .filter(volume_count__gt=1)
            .order_by("name")
        )
        all_excluded_series_by_publisher = {}
        for series in all_excluded_series:
            all_excluded_series_by_publisher.setdefault(
                (series["publisher_id"], series["series_type_id"]), []
            ).append(series)

        for pub in pubs:
            for st in series_types_qs:
                key = (pub.id, st[0])
                if key in all_excluded_series_by_publisher:
                    for i in all_excluded_series_by_publisher[key]:
                        self.stdout.write(
                            self.style.ERROR(
                                f"{i['name']} | {i['volume_count']} Duplicates | {pub} "
                            )
                        )
