"""Fixtures for polls app tests."""

from datetime import timedelta

import pytest
from django.utils import timezone

from polls.models import Poll, PollChoice, PollVote


@pytest.fixture
def poll_user(db, create_user):
    return create_user(username="poll_user")


@pytest.fixture
def other_poll_user(db, create_user):
    return create_user(username="other_poll_user")


@pytest.fixture
def active_poll(db, poll_user):
    now = timezone.now()
    poll = Poll.objects.create(
        title="Active Poll",
        description="An active poll for testing",
        created_by=poll_user,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=6),
    )
    PollChoice.objects.create(poll=poll, text="Choice A", order=1)
    PollChoice.objects.create(poll=poll, text="Choice B", order=2)
    return poll


@pytest.fixture
def upcoming_poll(db, poll_user):
    now = timezone.now()
    poll = Poll.objects.create(
        title="Upcoming Poll",
        description="An upcoming poll for testing",
        created_by=poll_user,
        start_date=now + timedelta(days=1),
        end_date=now + timedelta(days=7),
    )
    PollChoice.objects.create(poll=poll, text="Yes", order=1)
    PollChoice.objects.create(poll=poll, text="No", order=2)
    return poll


@pytest.fixture
def closed_poll(db, poll_user):
    now = timezone.now()
    poll = Poll.objects.create(
        title="Closed Poll",
        description="A closed poll for testing",
        created_by=poll_user,
        start_date=now - timedelta(days=7),
        end_date=now - timedelta(days=1),
    )
    PollChoice.objects.create(poll=poll, text="Option 1", order=1)
    PollChoice.objects.create(poll=poll, text="Option 2", order=2)
    return poll


@pytest.fixture
def active_poll_with_vote(active_poll, poll_user):
    choice = active_poll.choices.first()
    PollVote.objects.create(poll=active_poll, choice=choice, user=poll_user)
    return active_poll
