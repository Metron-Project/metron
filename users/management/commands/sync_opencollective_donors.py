from datetime import UTC, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from users.models import CustomUser, OpenCollectiveDonation, tier_for_amount
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

        # OpenCollective returns newest-first; the supporter_until stacking recurrence
        # (and the monthly-total combination below) are only order-independent when
        # applied oldest-first, so sort ascending before processing.
        contributions = sorted(contributions, key=self._contribution_sort_key)

        known_transaction_ids = set(
            OpenCollectiveDonation.objects.filter(
                transaction_id__in=[str(c["id"]) for c in contributions]
            ).values_list("transaction_id", flat=True)
        )

        counts = {
            "matched": 0,
            "unmatched": 0,
            "ambiguous": 0,
            "already_processed": 0,
            "below_minimum": 0,
        }
        pending_until: dict[int, datetime] = {}
        pending_month_totals: dict[tuple[int, int, int], int] = {}
        for contribution in contributions:
            result = self._process_contribution(
                contribution, known_transaction_ids, dry_run, pending_until, pending_month_totals
            )
            counts[result] += 1

        self._print_summary(dry_run, counts)

    @staticmethod
    def _contribution_sort_key(contribution: dict) -> datetime:
        parsed = parse_datetime(contribution["createdAt"])
        # Unparseable dates sort first; _process_contribution rejects them
        # individually regardless of position, so this only affects their
        # relative order among other bad rows, never a real one.
        return parsed or datetime.min.replace(tzinfo=UTC)

    def _process_contribution(
        self,
        contribution: dict,
        known_transaction_ids: set[str],
        dry_run: bool,
        pending_until: dict[int, datetime],
        pending_month_totals: dict[tuple[int, int, int], int],
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

        return self._grant_supporter_status(
            donation, user, dry_run, pending_until, pending_month_totals
        )

    def _grant_supporter_status(
        self,
        donation: dict,
        user: CustomUser,
        dry_run: bool,
        pending_until: dict[int, datetime],
        pending_month_totals: dict[tuple[int, int, int], int],
    ) -> str:
        transaction_id = donation["transaction_id"]
        donated_at = donation["donated_at"]

        month_total = self._accumulate_month_total(
            user, donated_at, donation["amount"], pending_month_totals
        )
        tier = tier_for_amount(month_total)

        if tier is None:
            self.stdout.write(
                self.style.WARNING(
                    f"  Transaction {transaction_id}: {user.username}'s "
                    f"{donated_at:%B %Y} total ({month_total}c) is below the minimum "
                    "supporter tier - recording only, no elevated limit granted"
                )
            )
            if not dry_run:
                self._record_donation(donation, user=user)
            return "below_minimum"

        # supporter_until stacking is unchanged: still per-donation, still keyed on
        # the donation's own date, independent of the monthly combination above. Only
        # the tier (i.e. which daily limit applies while is_supporter is True) is now
        # driven by month_total instead of this donation's own amount.
        current_until = pending_until.get(user.pk, user.supporter_until)
        new_until = max(current_until or donated_at, donated_at) + SUPPORTER_DURATION
        pending_until[user.pk] = new_until

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Transaction {transaction_id}: would extend {user.username}'s supporter "
                    f"status to {new_until.isoformat()} at the {tier} tier "
                    f"(month total {month_total}c)"
                )
            )
            return "matched"

        with transaction.atomic():
            user.supporter_until = new_until
            user.supporter_tier = tier
            user.save(update_fields=["supporter_until", "supporter_tier"])
            self._record_donation(donation, user=user)

        self.stdout.write(
            self.style.SUCCESS(
                f"  Transaction {transaction_id}: extended {user.username}'s supporter status "
                f"to {new_until.isoformat()} at the {tier} tier"
            )
        )
        return "matched"

    @staticmethod
    def _accumulate_month_total(
        user: CustomUser,
        donated_at: datetime,
        amount: int,
        pending_month_totals: dict[tuple[int, int, int], int],
    ) -> int:
        """Total cents donated by `user` in `donated_at`'s local calendar month across
        all matched donations, including this one. Seeded from the DB the first time a
        given user+month is touched in this run (dry-run never persists, so this can't
        just re-query each time), then accumulated in-memory for later donations in
        the same run/month."""
        local_donated_at = timezone.localtime(donated_at)
        key = (user.pk, local_donated_at.year, local_donated_at.month)
        if key not in pending_month_totals:
            existing_total = sum(
                d.amount
                for d in OpenCollectiveDonation.objects.filter(user=user).only(
                    "amount", "donated_at"
                )
                if timezone.localtime(d.donated_at).year == local_donated_at.year
                and timezone.localtime(d.donated_at).month == local_donated_at.month
            )
            pending_month_totals[key] = existing_total
        pending_month_totals[key] += amount
        return pending_month_totals[key]

    def _print_summary(self, dry_run: bool, counts: dict[str, int]) -> None:
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 50))
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes were made"))
        self.stdout.write(self.style.SUCCESS(f"Matched: {counts['matched']}"))
        if counts["below_minimum"]:
            self.stdout.write(
                self.style.WARNING(f"Below minimum tier (recorded only): {counts['below_minimum']}")
            )
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
