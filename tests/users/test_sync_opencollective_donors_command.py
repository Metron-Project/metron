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
        assert confirmed_user.supporter_tier == "backer"

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
        # Two 500c donations combine to 1000c this month -> crosses into Sponsor.
        assert confirmed_user.supporter_tier == "sponsor"

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

    # -----------------------------------------------------------------------
    # Tiered rate limits based on donation amount
    # -----------------------------------------------------------------------

    def test_donation_below_friend_minimum_alone_is_recorded_but_grants_nothing(
        self, confirmed_user
    ):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-low", confirmed_user.email, cents=199)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert confirmed_user.is_supporter is False
        assert confirmed_user.supporter_tier == ""
        donation = OpenCollectiveDonation.objects.get(transaction_id="txn-low")
        assert donation.user == confirmed_user

    def test_below_minimum_donations_combine_within_month_to_cross_threshold(self, confirmed_user):
        day1 = timezone.now().replace(day=1, hour=12, minute=0, second=0, microsecond=0)
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-part-1", confirmed_user.email, cents=100, created_at=day1),
                _contribution(
                    "txn-part-2",
                    confirmed_user.email,
                    cents=150,
                    created_at=day1 + timedelta(days=1),
                ),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        # 100 + 150 = 250c -> crosses the 200c Friend minimum on the second donation.
        assert confirmed_user.is_supporter is True
        assert confirmed_user.supporter_tier == "friend"

    def test_same_month_donations_combine_to_reach_higher_tier(self, confirmed_user):
        day1 = timezone.now().replace(day=1, hour=12, minute=0, second=0, microsecond=0)
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-c1", confirmed_user.email, cents=500, created_at=day1),
                _contribution(
                    "txn-c2",
                    confirmed_user.email,
                    cents=2500,
                    created_at=day1 + timedelta(days=15),
                ),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        # 500 + 2500 = 3000c this month -> Mega Sponsor, not just the tier either
        # donation alone would imply.
        assert confirmed_user.supporter_tier == "mega_sponsor"

    def test_different_calendar_months_do_not_combine(self, confirmed_user):
        month1 = timezone.now().replace(day=1, hour=12, minute=0, second=0, microsecond=0)
        next_month = (month1 + timedelta(days=32)).replace(day=1)
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-m1", confirmed_user.email, cents=150, created_at=month1),
                _contribution("txn-m2", confirmed_user.email, cents=150, created_at=next_month),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        # 150c alone in each of two separate months never crosses the 200c Friend
        # minimum -> below_minimum both times, since months don't combine.
        assert confirmed_user.is_supporter is False
        assert confirmed_user.supporter_tier == ""

    def test_later_month_with_lower_total_does_not_retroactively_change_earlier_grant(
        self, confirmed_user
    ):
        month1 = timezone.now().replace(day=1, hour=12, minute=0, second=0, microsecond=0)
        next_month = (month1 + timedelta(days=32)).replace(day=1)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-hi", confirmed_user.email, cents=3000, created_at=month1)
            ],
        ):
            call_command("sync_opencollective_donors")
        confirmed_user.refresh_from_db()
        assert confirmed_user.supporter_tier == "mega_sponsor"

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-lo", confirmed_user.email, cents=150, created_at=next_month)
            ],
        ):
            call_command("sync_opencollective_donors")
        confirmed_user.refresh_from_db()
        # The below-minimum next-month donation touches neither supporter_until nor
        # tier; last month's mega_sponsor grant is untouched.
        assert confirmed_user.supporter_tier == "mega_sponsor"

    def test_summary_counts_below_minimum_outcome(self, confirmed_user, capsys):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-summary-low", confirmed_user.email, cents=100)],
        ):
            call_command("sync_opencollective_donors")

        captured = capsys.readouterr()
        assert "Below minimum tier (recorded only): 1" in captured.out

    def test_dry_run_previews_month_combination_across_multiple_donations(self, confirmed_user):
        day1 = timezone.now().replace(day=1, hour=12, minute=0, second=0, microsecond=0)
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-dry-1", confirmed_user.email, cents=100, created_at=day1),
                _contribution(
                    "txn-dry-2",
                    confirmed_user.email,
                    cents=2500,
                    created_at=day1 + timedelta(days=2),
                ),
            ],
        ):
            call_command("sync_opencollective_donors", "--dry-run")

        confirmed_user.refresh_from_db()
        assert confirmed_user.is_supporter is False  # dry-run never persists
        assert confirmed_user.supporter_tier == ""
        assert OpenCollectiveDonation.objects.count() == 0

    def test_processing_order_is_ascending_regardless_of_api_response_order(self, confirmed_user):
        """Regression test for the stacking-inflation bug: feed contributions in
        descending (newest-first) order, exactly like the real OpenCollective API
        does, and assert the CORRECT ascending-equivalent result, not the inflated
        one a naive as-received loop would produce."""
        older = timezone.now() - timedelta(days=40)
        newer = older + timedelta(days=30)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-newer", confirmed_user.email, cents=500, created_at=newer),
                _contribution("txn-older", confirmed_user.email, cents=500, created_at=older),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        expected = older + timedelta(days=31) + timedelta(days=31)
        assert abs((confirmed_user.supporter_until - expected).total_seconds()) < 1
        # The inflated (buggy, descending-processed) result would be newer + 62 days,
        # roughly 30 days later than the correct value - assert we're not there.
        inflated = newer + timedelta(days=62)
        assert (inflated - confirmed_user.supporter_until).total_seconds() > 25 * 86400
