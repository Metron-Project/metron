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
RECURRING_FREQUENCIES = {"monthly", "yearly"}

# (donated_at, amount_cents, is_recurring) history entries used to reconstruct a
# donor's current "supporter period" bucket.
HistoryEntry = tuple[datetime, int, bool]


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

        # OpenCollective returns newest-first; the supporter-period bucket walk below
        # is only order-independent when applied oldest-first, so sort ascending.
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
        pending_history: dict[int, list[HistoryEntry]] = {}
        for contribution in contributions:
            result = self._process_contribution(
                contribution, known_transaction_ids, dry_run, pending_history
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
        pending_history: dict[int, list[HistoryEntry]],
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

        frequency = ((contribution.get("order") or {}).get("frequency") or "onetime").lower()

        donation = {
            "transaction_id": transaction_id,
            "email": email,
            "amount": contribution["amount"]["valueInCents"],
            "donated_at": donated_at,
            "frequency": frequency,
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

        return self._grant_supporter_status(donation, user, dry_run, pending_history)

    def _grant_supporter_status(
        self,
        donation: dict,
        user: CustomUser,
        dry_run: bool,
        pending_history: dict[int, list[HistoryEntry]],
    ) -> str:
        transaction_id = donation["transaction_id"]
        donated_at = donation["donated_at"]
        amount = donation["amount"]
        is_recurring = donation["frequency"] in RECURRING_FREQUENCIES

        history = self._get_user_history(user, pending_history)
        _, bucket_total_before = self._current_bucket(history)
        history.append((donated_at, amount, is_recurring))
        bucket_start, bucket_total = self._current_bucket(history)

        tier = tier_for_amount(bucket_total)

        if tier is None:
            self.stdout.write(
                self.style.WARNING(
                    f"  Transaction {transaction_id}: {user.username}'s current period total "
                    f"({bucket_total}c since {bucket_start:%Y-%m-%d}) is below the minimum "
                    "supporter tier - recording only, no elevated limit granted"
                )
            )
            if not dry_run:
                self._record_donation(donation, user=user)
            return "below_minimum"

        new_until = bucket_start + SUPPORTER_DURATION
        # A recurring charge is always its own new period, regardless of whether the
        # prior period (now discarded) happened to be qualified. A one-time donation
        # only counts as extending time if the bucket it's joining wasn't already
        # granting a tier - otherwise it's just a same-period tier upgrade.
        extends_time = is_recurring or tier_for_amount(bucket_total_before) is None
        grant = (tier, new_until)

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(self._grant_message(transaction_id, user, grant, extends_time))
            )
            return "matched"

        with transaction.atomic():
            user.supporter_until = new_until
            user.supporter_tier = tier
            user.save(update_fields=["supporter_until", "supporter_tier"])
            self._record_donation(donation, user=user)

        self.stdout.write(
            self.style.SUCCESS(
                self._grant_message(transaction_id, user, grant, extends_time, would=False)
            )
        )
        return "matched"

    @staticmethod
    def _grant_message(transaction_id, user, grant, extends_time, *, would=True):
        tier, new_until = grant
        if extends_time:
            verb = "would extend" if would else "extended"
            return (
                f"  Transaction {transaction_id}: {verb} {user.username}'s supporter status "
                f"to {new_until.isoformat()} at the {tier} tier"
            )
        upgrade_verb = "would upgrade" if would else "upgraded"
        return (
            f"  Transaction {transaction_id}: {upgrade_verb} {user.username} to the {tier} tier "
            "for the current period (no additional time added)"
        )

    @staticmethod
    def _get_user_history(
        user: CustomUser, pending_history: dict[int, list[HistoryEntry]]
    ) -> list[HistoryEntry]:
        if user.pk not in pending_history:
            pending_history[user.pk] = [
                (d.donated_at, d.amount, d.frequency in RECURRING_FREQUENCIES)
                for d in OpenCollectiveDonation.objects.filter(user=user).only(
                    "donated_at", "amount", "frequency"
                )
            ]
        return pending_history[user.pk]

    @staticmethod
    def _current_bucket(history: list[HistoryEntry]) -> tuple[datetime | None, int]:
        """Replay a user's donation history to find the anchor date and cumulative
        total of the "current" supporter period (the bucket the most recent entry
        belongs to).

        A recurring donation always starts a fresh period (each billing cycle is its
        own period, even if it lands well within the previous period's 31 days - a
        $2/mo donor's charges are ~30 days apart, always inside the prior window).
        A one-time donation joins the current period if it falls within 31 days of
        that period's anchor (whether or not that period has already qualified for a
        tier), otherwise it starts a fresh period of its own.
        """
        bucket_start = None
        bucket_total = 0
        for dt, amt, is_recurring in sorted(history, key=lambda entry: entry[0]):
            if is_recurring or bucket_start is None or dt >= bucket_start + SUPPORTER_DURATION:
                bucket_start = dt
                bucket_total = 0
            bucket_total += amt
        return bucket_start, bucket_total

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
