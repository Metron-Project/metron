from django.core.management.base import BaseCommand

from comicsdb.models.issue import Issue


class Command(BaseCommand):
    help = "Fix bad issue story data."

    def handle(self, *args, **options):
        if fix_count := Issue.objects.filter(name=None).update(name=[]):
            self.stdout.write(self.style.SUCCESS(f"Fixed {fix_count} issues."))
        else:
            self.stdout.write(self.style.WARNING("Nothing to fix."))
