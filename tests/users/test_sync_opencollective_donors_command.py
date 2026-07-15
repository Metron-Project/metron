"""Tests for the sync_opencollective_donors management command."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from users.models import OpenCollectiveDonation


def _contribution(transaction_id, email, cents=500, created_at=None, frequency="MONTHLY"):
    created_at = created_at or timezone.now()
    return {
        "id": transaction_id,
        "createdAt": created_at.isoformat(),
        "amount": {"valueInCents": cents},
        "fromAccount": {"email": email},
        "order": {"frequency": frequency},
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

    def test_fresh_donation_with_no_prior_history_starts_its_own_date(self, confirmed_user):
        confirmed_user.supporter_until = timezone.now() - timedelta(days=20)
        confirmed_user.save()
        donated_at = timezone.now() - timedelta(days=3)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-recent", confirmed_user.email, created_at=donated_at)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        # supporter_until/tier are reconstructed purely from OpenCollectiveDonation
        # history, not from whatever was previously (directly) stored on the user -
        # with no prior recorded donation, this one starts fresh from its own date.
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

    def test_repeat_recurring_donation_stacks_on_existing_supporter_window(self, confirmed_user):
        first_donated_at = timezone.now() - timedelta(days=20)
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-6a", confirmed_user.email, created_at=first_donated_at)
            ],
        ):
            call_command("sync_opencollective_donors")
        confirmed_user.refresh_from_db()
        first_until = confirmed_user.supporter_until

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-6b", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert confirmed_user.supporter_until > first_until

    def test_onetime_topup_within_active_window_upgrades_tier_without_extra_time(
        self, confirmed_user
    ):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-a", confirmed_user.email, frequency="MONTHLY"),
                _contribution("txn-b", confirmed_user.email, frequency="ONETIME"),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        # Two 500c donations combine to 1000c -> crosses into Sponsor, but the
        # recurring charge is the only one that extends supporter_until - the
        # one-time top-up only upgrades the tier.
        assert confirmed_user.supporter_tier == "sponsor"
        assert confirmed_user.supporter_until < timezone.now() + timedelta(days=32)

    def test_already_processed_transaction_is_not_reprocessed(self, confirmed_user):
        OpenCollectiveDonation.objects.create(
            transaction_id="txn-7",
            user=confirmed_user,
            email=confirmed_user.email,
            amount=500,
            donated_at=timezone.now(),
            frequency="monthly",
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
        confirmed_user.refresh_from_db()
        first_until = confirmed_user.supporter_until

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-month-2", confirmed_user.email)],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert OpenCollectiveDonation.objects.filter(user=confirmed_user).count() == 2
        assert confirmed_user.supporter_until > first_until

    def test_recurring_charges_keep_advancing_supporter_until_each_period(self, confirmed_user):
        """Regression guard: a pure recurring monthly donor's supporter_until must
        keep advancing every period, even though each charge lands well within the
        previous period's 31 days (a $2/mo donor's charges are ~30 days apart) -
        combining "anything within the rolling window" would otherwise freeze
        supporter_until at the first charge forever."""
        charge1 = timezone.now() - timedelta(days=60)
        charge2 = charge1 + timedelta(days=30)
        charge3 = charge2 + timedelta(days=30)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution("txn-r1", confirmed_user.email, cents=200, created_at=charge1),
                _contribution("txn-r2", confirmed_user.email, cents=200, created_at=charge2),
                _contribution("txn-r3", confirmed_user.email, cents=200, created_at=charge3),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        expected_until = charge3 + timedelta(days=31)
        assert abs((confirmed_user.supporter_until - expected_until).total_seconds()) < 1
        # Each period is evaluated independently, so the tier reflects only the
        # latest charge, not a cumulative total across all periods.
        assert confirmed_user.supporter_tier == "friend"

    def test_recurring_charge_and_later_onetime_topup_combine_within_the_same_period(
        self, confirmed_user
    ):
        """Mirrors the motivating example: a recurring monthly charge, followed by a
        one-time top-up ~3 weeks later. Whether or not that crosses a calendar-month
        boundary no longer matters, since combination is based on the donor's
        rolling 31-day period, not the calendar."""
        recurring_charge = timezone.now() - timedelta(days=10)
        topup = recurring_charge + timedelta(days=20)

        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution(
                    "txn-recurring",
                    confirmed_user.email,
                    cents=200,
                    created_at=recurring_charge,
                    frequency="MONTHLY",
                ),
                _contribution(
                    "txn-topup",
                    confirmed_user.email,
                    cents=800,
                    created_at=topup,
                    frequency="ONETIME",
                ),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        assert confirmed_user.supporter_tier == "sponsor"  # 200 + 800 = 1000c
        expected_until = recurring_charge + timedelta(days=31)
        assert abs((confirmed_user.supporter_until - expected_until).total_seconds()) < 1

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

    def test_below_minimum_onetime_donations_combine_within_period_to_cross_threshold(
        self, confirmed_user
    ):
        day1 = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution(
                    "txn-part-1",
                    confirmed_user.email,
                    cents=100,
                    created_at=day1,
                    frequency="ONETIME",
                ),
                _contribution(
                    "txn-part-2",
                    confirmed_user.email,
                    cents=150,
                    created_at=day1 + timedelta(days=1),
                    frequency="ONETIME",
                ),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        # 100 + 150 = 250c -> crosses the 200c Friend minimum on the second donation.
        assert confirmed_user.is_supporter is True
        assert confirmed_user.supporter_tier == "friend"
        expected_until = day1 + timedelta(days=31)
        assert abs((confirmed_user.supporter_until - expected_until).total_seconds()) < 1

    def test_onetime_donations_more_than_31_days_apart_do_not_combine(self, confirmed_user):
        day1 = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        later = day1 + timedelta(days=40)
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution(
                    "txn-m1", confirmed_user.email, cents=150, created_at=day1, frequency="ONETIME"
                ),
                _contribution(
                    "txn-m2",
                    confirmed_user.email,
                    cents=150,
                    created_at=later,
                    frequency="ONETIME",
                ),
            ],
        ):
            call_command("sync_opencollective_donors")

        confirmed_user.refresh_from_db()
        # 150c alone never crosses the 200c Friend minimum, and the two donations
        # are more than 31 days apart -> below_minimum both times, never combined.
        assert confirmed_user.is_supporter is False
        assert confirmed_user.supporter_tier == ""

    def test_later_low_onetime_donation_does_not_retroactively_change_earlier_grant(
        self, confirmed_user
    ):
        month1 = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        later = month1 + timedelta(days=40)

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
                _contribution(
                    "txn-lo",
                    confirmed_user.email,
                    cents=150,
                    created_at=later,
                    frequency="ONETIME",
                )
            ],
        ):
            call_command("sync_opencollective_donors")
        confirmed_user.refresh_from_db()
        # The below-minimum later donation (a new, separate period, since it's more
        # than 31 days after the first) touches neither supporter_until nor tier;
        # the earlier mega_sponsor grant is untouched.
        assert confirmed_user.supporter_tier == "mega_sponsor"

    def test_summary_counts_below_minimum_outcome(self, confirmed_user, capsys):
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[_contribution("txn-summary-low", confirmed_user.email, cents=100)],
        ):
            call_command("sync_opencollective_donors")

        captured = capsys.readouterr()
        assert "Below minimum tier (recorded only): 1" in captured.out

    def test_dry_run_previews_period_combination_across_multiple_donations(self, confirmed_user):
        day1 = timezone.now().replace(hour=12, minute=0, second=0, microsecond=0)
        with patch(
            "users.management.commands.sync_opencollective_donors.fetch_recent_contributions",
            return_value=[
                _contribution(
                    "txn-dry-1",
                    confirmed_user.email,
                    cents=100,
                    created_at=day1,
                    frequency="ONETIME",
                ),
                _contribution(
                    "txn-dry-2",
                    confirmed_user.email,
                    cents=2500,
                    created_at=day1 + timedelta(days=2),
                    frequency="ONETIME",
                ),
            ],
        ):
            call_command("sync_opencollective_donors", "--dry-run")

        confirmed_user.refresh_from_db()
        assert confirmed_user.is_supporter is False  # dry-run never persists
        assert confirmed_user.supporter_tier == ""
        assert OpenCollectiveDonation.objects.count() == 0

    def test_processing_order_is_ascending_regardless_of_api_response_order(self, confirmed_user):
        """Regression test: feed contributions in descending (newest-first) order,
        exactly like the real OpenCollective API does, and assert the CORRECT
        ascending-equivalent result, not what reverse-order processing would give."""
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
        # Correct (ascending-processed): the later recurring charge is the one that
        # determines the final period, extending 31 days from its own date.
        expected = newer + timedelta(days=31)
        assert abs((confirmed_user.supporter_until - expected).total_seconds()) < 1
        # If processed newest-first, the older donation would be applied LAST and
        # incorrectly overwrite supporter_until with an earlier date.
        wrong_if_reverse_processed = older + timedelta(days=31)
        assert confirmed_user.supporter_until > wrong_if_reverse_processed
