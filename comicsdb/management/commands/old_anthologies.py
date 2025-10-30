from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from comicsdb.models import Series
from comicsdb.models.credits import Credits, Role
from comicsdb.models.issue import Issue


class Command(BaseCommand):
    help = "Fix old anthology roles"

    def _remove_desc(self, series: Series) -> None:
        qs = Issue.objects.filter(series=series)
        for i in qs:
            i.desc = ""
        Issue.objects.bulk_update(qs, ["desc"])
        self.stdout.write(self.style.SUCCESS(f"Removed story summary for {len(qs)} issues"))

    def _correct_roles(self, credit: Credits, good: Role, bad: list[Role]) -> bool:
        fix = False
        if all(i in credit.role.all() for i in bad):
            fix = True
            for role in bad:
                credit.role.remove(role)
            if good not in credit.role.all():
                credit.role.add(good)
            self.stdout.write(
                self.style.SUCCESS(f"Fixed {good} credit in {credit.issue} for {credit.creator}")
            )
        return fix

    def _fix_credits(self, series: Series) -> None:
        writer = Role.objects.get(name__iexact="writer")
        story = Role.objects.get(name__iexact="story")
        pencil = Role.objects.get(name__iexact="penciller")
        ink = Role.objects.get(name__iexact="inker")
        artist = Role.objects.get(name__iexact="artist")

        qs = Credits.objects.filter(issue__series=series)

        for i in qs:
            # Fix writing credits.
            fix_writer = self._correct_roles(i, story, [writer])

            # Fix art credits
            fix_artist = self._correct_roles(i, artist, [pencil, ink])

            if not fix_writer and not fix_artist:
                self.stdout.write(
                    self.style.WARNING(f"Nothing to fix in {i.issue} for {i.creator}")
                )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--series", type=int, required=True, help="Series ID")
        parser.add_argument(
            "--delete-desc", action="store_true", help="Delete issue descriptions for series."
        )
        parser.add_argument(
            "--fix-credits", action="store_true", help="Fix creator credits for series.ss."
        )
        return super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> None:
        if not options["delete_desc"] and not options["fix_credits"]:
            self.stdout.write(self.style.WARNING("No action options given. Exiting..."))
            return
        series = Series.objects.get(id=options["series"])
        if options["fix_credits"]:
            self._fix_credits(series)

        if options["delete_desc"]:
            self._remove_desc(series)
