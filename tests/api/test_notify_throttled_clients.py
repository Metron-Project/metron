import io
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from api.client_health import RepeatOffender
from api.models import ThrottleNotice
from users.models import ApiToken

COMMAND = "notify_throttled_clients"


def _offender(user, **overrides):
    defaults = {"days_throttled": 3, "total_count": 15, "worst_day_count": 5}
    defaults.update(overrides)
    return RepeatOffender(username=user.username, **defaults)


def _add_prior_notices(user, count):
    """Create `count` ThrottleNotice rows for `user`, backdated outside the
    default cooldown window so they don't get skipped as "too recent"."""
    for _ in range(count):
        notice = ThrottleNotice.objects.create(
            user=user, days_throttled=3, total_count=15, worst_day_count=5
        )
        ThrottleNotice.objects.filter(pk=notice.pk).update(
            sent_at=timezone.now() - timedelta(days=10)
        )


@pytest.fixture
def mock_send_pushover():
    with patch("api.management.commands.notify_throttled_clients.send_pushover") as mock:
        yield mock


@pytest.mark.django_db
def test_report_only_sends_no_email_and_creates_no_notice(
    create_user, mailoutbox, mock_send_pushover
):
    user = create_user(email_confirmed=True)
    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[_offender(user)],
    ):
        call_command(COMMAND)

    assert len(mailoutbox) == 0
    assert ThrottleNotice.objects.count() == 0
    mock_send_pushover.assert_called_once()


@pytest.mark.django_db
def test_send_flag_emails_eligible_candidate_and_records_notice(
    create_user, mailoutbox, mock_send_pushover
):
    user = create_user(email_confirmed=True)
    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[_offender(user)],
    ):
        call_command(COMMAND, send=True)

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == [user.email]
    assert "15 rate-limited (429) responses" in mailoutbox[0].body
    assert "3 days" in mailoutbox[0].body
    notice = ThrottleNotice.objects.get(user=user)
    assert notice.days_throttled == 3
    assert notice.total_count == 15
    assert notice.worst_day_count == 5


@pytest.mark.django_db
def test_skips_candidate_without_confirmed_email(create_user, mailoutbox, mock_send_pushover):
    user = create_user()  # email_confirmed defaults to False
    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[_offender(user)],
    ):
        call_command(COMMAND, send=True)

    assert len(mailoutbox) == 0
    assert ThrottleNotice.objects.count() == 0
    mock_send_pushover.assert_not_called()


@pytest.mark.django_db
def test_skips_candidate_within_cooldown(create_user, mailoutbox, mock_send_pushover):
    user = create_user(email_confirmed=True)
    ThrottleNotice.objects.create(user=user, days_throttled=3, total_count=15, worst_day_count=5)

    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[_offender(user)],
    ):
        call_command(COMMAND, send=True)

    assert len(mailoutbox) == 0
    assert ThrottleNotice.objects.filter(user=user).count() == 1
    mock_send_pushover.assert_not_called()


@pytest.mark.django_db
def test_no_candidates_does_not_notify_pushover(mailoutbox, mock_send_pushover):
    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[],
    ):
        call_command(COMMAND)

    assert len(mailoutbox) == 0
    mock_send_pushover.assert_not_called()


# ---------------------------------------------------------------------------
# --enforce
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_enforce_revokes_tokens_when_present(create_user, mailoutbox, mock_send_pushover):
    user = create_user(email_confirmed=True)
    ApiToken.objects.create(user=user, name="test token")
    _add_prior_notices(user, count=2)  # this run's notice will be the 3rd

    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[_offender(user)],
    ):
        call_command(COMMAND, send=True, enforce=True)

    user.refresh_from_db()
    assert user.is_active is True
    assert user.auth_token_set.count() == 0
    assert len(mailoutbox) == 1
    assert "restricted" in mailoutbox[0].subject
    assert "15 rate-limited (429) responses" in mailoutbox[0].body
    assert ThrottleNotice.objects.filter(user=user).count() == 3


@pytest.mark.django_db
def test_enforce_disables_account_when_no_tokens(create_user, mailoutbox, mock_send_pushover):
    user = create_user(email_confirmed=True)
    _add_prior_notices(user, count=2)

    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[_offender(user)],
    ):
        call_command(COMMAND, send=True, enforce=True)

    user.refresh_from_db()
    assert user.is_active is False
    assert len(mailoutbox) == 1
    assert "restricted" in mailoutbox[0].subject


@pytest.mark.django_db
def test_enforce_not_applied_before_enforce_after_threshold(
    create_user, mailoutbox, mock_send_pushover
):
    user = create_user(email_confirmed=True)
    _add_prior_notices(user, count=1)  # only 1 prior notice, default enforce_after is 2

    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[_offender(user)],
    ):
        call_command(COMMAND, send=True, enforce=True)

    user.refresh_from_db()
    assert user.is_active is True
    assert len(mailoutbox) == 1
    assert "rate-limited" in mailoutbox[0].subject


@pytest.mark.django_db
def test_report_mode_previews_enforcement_without_side_effects(
    create_user, mailoutbox, mock_send_pushover
):
    user = create_user(email_confirmed=True)
    ApiToken.objects.create(user=user, name="test token")
    _add_prior_notices(user, count=2)

    out = io.StringIO()
    with patch(
        "api.management.commands.notify_throttled_clients.find_repeat_offenders",
        return_value=[_offender(user)],
    ):
        call_command(COMMAND, enforce=True, stdout=out)

    user.refresh_from_db()
    assert "Would enforce (revoke tokens)" in out.getvalue()
    assert user.is_active is True
    assert user.auth_token_set.count() == 1
    assert len(mailoutbox) == 0
    assert ThrottleNotice.objects.filter(user=user).count() == 2
