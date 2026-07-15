from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from users.models import CustomUser, OpenCollectiveDonation
from users.opencollective import fetch_recent_contributions

DEFAULT_LOOKBACK_DAYS = 60
SUPPORTER_DURATION = timedelta(days=31)


class Command(BaseCommand):
    help = "Sync recent OpenCollective donations and grant matching users elevated API rate limits"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would change without writing to the database",
        )
        parser.add_argument(
            "--since",
            type=str,
            default=None,
            help=(
                "Only import donations on or after this date (YYYY-MM-DD), overriding the "
                "usual auto-detected cutoff. Useful for the very first run, to exclude older "
                "donations. Subsequent runs resume from the latest imported donation as usual."
            ),
        )

    def handle(self, *args, **options) -> None:
        dry_run = options["dry_run"]
        since = self._get_since(options["since"])

        self.stdout.write(f"Fetching OpenCollective contributions since {since.isoformat()}")
        contributions = fetch_recent_contributions(since)

        known_transaction_ids = set(
            OpenCollectiveDonation.objects.filter(
                transaction_id__in=[str(c["id"]) for c in contributions]
            ).values_list("transaction_id", flat=True)
        )

        counts = {"matched": 0, "unmatched": 0, "ambiguous": 0, "already_processed": 0}
        pending_until: dict[int, datetime] = {}
        for contribution in contributions:
            result = self._process_contribution(
                contribution, known_transaction_ids, dry_run, pending_until
            )
            counts[result] += 1

        self._print_summary(dry_run, counts)

    def _process_contribution(
        self,
        contribution: dict,
        known_transaction_ids: set[str],
        dry_run: bool,
        pending_until: dict[int, datetime],
    ) -> str:
        transaction_id = str(contribution["id"])
        if transaction_id in known_transaction_ids:
            return "already_processed"

        email = (contribution.get("fromAccount") or {}).get("email")
        if not email:
            self.stdout.write(
                self.style.WARNING(
                    f"  Transaction {transaction_id}: no donor email available - skipping"
                )
            )
            return "unmatched"

        donated_at = parse_datetime(contribution["createdAt"])
        if donated_at is None:
            self.stdout.write(
                self.style.WARNING(f"  Transaction {transaction_id}: unparseable date - skipping")
            )
            return "unmatched"

        donation = {
            "transaction_id": transaction_id,
            "email": email,
            "amount": contribution["amount"]["valueInCents"],
            "donated_at": donated_at,
        }

        candidates = list(CustomUser.objects.filter(email__iexact=email, email_confirmed=True))

        if len(candidates) > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"  Transaction {transaction_id}: multiple confirmed accounts match "
                    f"{email} - skipping"
                )
            )
            if not dry_run:
                self._record_donation(donation, user=None)
            return "ambiguous"

        user = candidates[0] if candidates else None
        if user is None:
            self.stdout.write(
                self.style.WARNING(
                    f"  Transaction {transaction_id}: no confirmed Metron account matches {email}"
                )
            )
            if not dry_run:
                self._record_donation(donation, user=None)
            return "unmatched"

        self._grant_supporter_status(donation, user, dry_run, pending_until)
        return "matched"

    def _grant_supporter_status(
        self, donation: dict, user: CustomUser, dry_run: bool, pending_until: dict[int, datetime]
    ) -> None:
        transaction_id = donation["transaction_id"]
        donated_at = donation["donated_at"]
        current_until = pending_until.get(user.pk, user.supporter_until)
        new_until = max(current_until or donated_at, donated_at) + SUPPORTER_DURATION
        pending_until[user.pk] = new_until

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Transaction {transaction_id}: would extend {user.username}'s supporter "
                    f"status to {new_until.isoformat()}"
                )
            )
            return

        with transaction.atomic():
            user.supporter_until = new_until
            user.save(update_fields=["supporter_until"])
            self._record_donation(donation, user=user)

        self.stdout.write(
            self.style.SUCCESS(
                f"  Transaction {transaction_id}: extended {user.username}'s supporter status "
                f"to {new_until.isoformat()}"
            )
        )

    def _print_summary(self, dry_run: bool, counts: dict[str, int]) -> None:
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 50))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        self.stdout.write(self.style.SUCCESS(f"Matched: {counts['matched']}"))
        if counts["unmatched"]:
            self.stdout.write(self.style.WARNING(f"Unmatched: {counts['unmatched']}"))
        if counts["ambiguous"]:
            self.stdout.write(
                self.style.WARNING(f"Ambiguous (multiple matches): {counts['ambiguous']}")
            )
        if counts["already_processed"]:
            self.stdout.write(
                self.style.SUCCESS(f"Already processed: {counts['already_processed']}")
            )

    @staticmethod
    def _get_since(since_override: str | None):
        if since_override:
            parsed = parse_datetime(since_override)
            if parsed is None:
                parsed_date = parse_date(since_override)
                if parsed_date is None:
                    raise CommandError(f"Invalid --since value: {since_override!r}")
                parsed = datetime.combine(parsed_date, datetime.min.time())
            return timezone.make_aware(parsed) if timezone.is_naive(parsed) else parsed

        latest = OpenCollectiveDonation.objects.aggregate(latest=Max("donated_at"))["latest"]
        if latest:
            return latest
        return timezone.now() - timedelta(days=DEFAULT_LOOKBACK_DAYS)

    @staticmethod
    def _record_donation(donation: dict, user: CustomUser | None) -> None:
        OpenCollectiveDonation.objects.create(user=user, **donation)
