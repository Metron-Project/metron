"""Tests for the sync_opencollective_donors management command."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from users.models import OpenCollectiveDonation


def _contribution(transaction_id, email, cents=500, created_at=None):
    created_at = created_at or timezone.now()
    return {
        "id": transaction_id,
        "createdAt": created_at.isoformat(),
        "amount": {"valueInCents": cents},
        "fromAccount": {"email": email},
    }


@pytest.fixture
def confirmed_user(create_user):
    return create_user(username="donor", email_confirmed=True)


@pytest.mark.django_db
class TestSyncOpenCollectiveDonorsCommand:
    def test_matches_confirmed_user_and_grants_supporter_status(self, confirmed_user):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-1", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert confirmed_user.is_supporter is True
        assert confirmed_user.supporter_until is not None

        donation = OpenCollectiveDonation.objects.get(transaction_id="txn-1")
        assert donation.user == confirmed_user
        assert donation.amount == 500

    def test_supporter_until_is_based_on_donation_date_not_run_time(self, confirmed_user):
        donated_at = timezone.now() - timedelta(days=5)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-old", confirmed_user.email, created_at=donated_at)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        expected = donated_at + timedelta(days=31)
        assert abs((confirmed_user.supporter_until - expected).total_seconds()) < 1

    def test_stacking_uses_donation_date_when_existing_status_expired(self, confirmed_user):
        confirmed_user.supporter_until = timezone.now() - timedelta(days=20)
        confirmed_user.save()
        donated_at = timezone.now() - timedelta(days=3)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-recent", confirmed_user.email, created_at=donated_at)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        expected = donated_at + timedelta(days=31)
        assert abs((confirmed_user.supporter_until - expected).total_seconds()) < 1

    def test_skips_unconfirmed_email_match(self, create_user):
        user = create_user(username="unconfirmed", email_confirmed=False)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-2", user.email)],
        ):
            call_command("sync_opencollective_donors")

        user.refresh_from_db()
        assert user.is_supporter is False

        donation = OpenCollectiveDonation.objects.get(transaction_id="txn-2")
        assert donation.user is None

    def test_no_matching_account_records_unmatched_donation(self):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-3", "nobody@example.com")],
        ):
            call_command("sync_opencollective_donors")

        donation = OpenCollectiveDonation.objects.get(transaction_id="txn-3")
        assert donation.user is None
        assert donation.email == "nobody@example.com"

    def test_ambiguous_matches_are_skipped(self, create_user):
        # create_user always assigns the shared `test_email` fixture value, so
        # two users created via this fixture naturally collide on email.
        user_a = create_user(username="user-a", email_confirmed=True)
        create_user(username="user-b", email_confirmed=True)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-4", user_a.email)],
        ):
            call_command("sync_opencollective_donors")

        user_a.refresh_from_db()
        assert user_a.is_supporter is False

        donation = OpenCollectiveDonation.objects.get(transaction_id="txn-4")
        assert donation.user is None

    def test_dry_run_makes_no_changes(self, confirmed_user):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-5", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors", "--dry-run")

        confirmed_user.refresh_from_db()
        assert confirmed_user.is_supporter is False
        assert OpenCollectiveDonation.objects.filter(transaction_id="txn-5").exists() is False

    def test_repeat_donation_stacks_on_existing_supporter_window(self, confirmed_user):
        confirmed_user.supporter_until = timezone.now() + timedelta(days=10)
        confirmed_user.save()
        existing_until = confirmed_user.supporter_until

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-6", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert confirmed_user.supporter_until > existing_until + timedelta(days=29)

    def test_multiple_donations_in_same_run_stack_on_each_other(self, confirmed_user):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-a", confirmed_user.email),
                _contribution("txn-b", confirmed_user.email),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert confirmed_user.supporter_until > timezone.now() + timedelta(days=60)

    def test_already_processed_transaction_is_not_reprocessed(self, confirmed_user):
        OpenCollectiveDonation.objects.create(
            transaction_id="txn-7",
            user=confirmed_user,
            email=confirmed_user.email,
            amount=500,
            donated_at=timezone.now(),
        )

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-7", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert confirmed_user.is_supporter is False
        assert OpenCollectiveDonation.objects.filter(transaction_id="txn-7").count() == 1

    def test_email_match_is_case_insensitive(self, confirmed_user):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-8", confirmed_user.email.upper())],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert confirmed_user.is_supporter is True

    def test_recurring_donor_second_month_charge_is_matched(self, confirmed_user):
        """A recurring subscription reuses one Order but creates a new Transaction each
        charge - the sync must key off the transaction id, not an order id, or a
        recurring donor's later months would never be picked up."""
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-month-1", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors")

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-month-2", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors")

        assert OpenCollectiveDonation.objects.filter(user=confirmed_user).count() == 2

    def test_since_option_overrides_default_lookback(self):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[],
        ) as mock_fetch:
            call_command("sync_opencollective_donors", "--since", "2026-07-01")

        called_since = mock_fetch.call_args[0][0]
        assert called_since.date().isoformat() == "2026-07-01"

    def test_since_option_rejects_invalid_date(self):
        with pytest.raises(CommandError, match="Invalid --since value"):
            call_command("sync_opencollective_donors", "--since", "not-a-date")

    def test_since_option_is_ignored_on_subsequent_runs(self, confirmed_user):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-since-1", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors", "--since", "2026-07-01")

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[],
        ) as mock_fetch:
            call_command("sync_opencollective_donors")

        called_since = mock_fetch.call_args[0][0]
        donation = OpenCollectiveDonation.objects.get(transaction_id="txn-since-1")
        assert called_since == donation.donated_at
