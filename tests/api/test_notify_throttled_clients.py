from unittest.mock import patch

import pytest
from django.core.management import call_command

from api.client_health import RepeatOffender
from api.models import ThrottleNotice

COMMAND = "notify_throttled_clients"


def _offender(user, **overrides):
    defaults = {"days_throttled": 3, "total_count": 15, "worst_day_count": 5}
    defaults.update(overrides)
    return RepeatOffender(username=user.username, **defaults)


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
