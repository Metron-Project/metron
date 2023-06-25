from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from comicsdb.models import Series
from comicsdb.models.credits import Credits, Role
from comicsdb.models.issue import Issue


class Command(BaseCommand):
    help = "Fix old anthology roles"

    @staticmethod
    def _remove_desc(series: Series) -> None:
        qs = Issue.objects.filter(series=series)
        for i in qs:
            i.desc = ""
        Issue.objects.bulk_update(qs, ["desc"])
        print(f"Removed story summary for {len(qs)} issues")

    @staticmethod
    def _fix_writer(credit: Credits) -> bool:
        fix = False
        writer = Role.objects.get(name__iexact="writer")
        story = Role.objects.get(name__iexact="story")

        if writer in credit.role.all():
            fix = True
            credit.role.remove(writer)
            if story not in credit.role.all():
                credit.role.add(story)
            print(f"Fixed {writer} role in {credit.issue} for {credit.creator}")
        return fix

    @staticmethod
    def _fix_artist(credit: Credits) -> bool:
        fix = False
        pencil = Role.objects.get(name__iexact="penciller")
        ink = Role.objects.get(name__iexact="inker")
        artist = Role.objects.get(name__iexact="artist")

        if pencil in credit.role.all() and ink in credit.role.all():
            fix = True
            credit.role.remove(pencil)
            credit.role.remove(ink)
            if artist not in credit.role.all():
                credit.role.add(artist)
            print(f"Fixed artist credit in {credit.issue} for {credit.creator}")
        return fix

    def _fix_credits(self, series: Series) -> None:
        qs = Credits.objects.filter(issue__series=series)

        for i in qs:
            # Fix writing credits.
            fix_writer = self._fix_writer(i)

            # Fix art credits
            fix_artist = self._fix_artist(i)

            if not fix_writer and not fix_artist:
                print(f"Nothing to fix in {i.issue} for {i.creator}")

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("slug", nargs="+", type=str)
        parser.add_argument(
            "--delete-desc", action="store_true", help="Delete issue descriptions for series."
        )
        parser.add_argument(
            "--fix-credits", action="store_true", help="Fix creator credits for series.ss."
        )
        return super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["delete_desc"] and not options["fix_credits"]:
            print("No action options given. Exiting...")
            return
        series = Series.objects.get(slug=options["slug"][0])
        if options["fix_credits"]:
            self._fix_credits(series)

        if options["delete_desc"]:
            self._remove_desc(series)
