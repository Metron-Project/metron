"""Tests for polls models."""

import pytest
from django.db import IntegrityError

from polls.models import Poll, PollVote

HTTP_200_OK = 200


class TestPollModel:
    def test_poll_creation(self, active_poll):
        assert isinstance(active_poll, Poll)
        assert active_poll.title == "Active Poll"
        assert active_poll.description == "An active poll for testing"

    def test_poll_str(self, active_poll):
        assert str(active_poll) == "Active Poll"

    def test_poll_absolute_url(self, client, active_poll):
        resp = client.get(active_poll.get_absolute_url())
        assert resp.status_code == HTTP_200_OK

    def test_poll_status_active(self, active_poll):
        assert active_poll.status == "active"
        assert active_poll.is_active
        assert not active_poll.is_upcoming
        assert not active_poll.is_closed

    def test_poll_status_upcoming(self, upcoming_poll):
        assert upcoming_poll.status == "upcoming"
        assert upcoming_poll.is_upcoming
        assert not upcoming_poll.is_active
        assert not upcoming_poll.is_closed

    def test_poll_status_closed(self, closed_poll):
        assert closed_poll.status == "closed"
        assert closed_poll.is_closed
        assert not closed_poll.is_active
        assert not closed_poll.is_upcoming

    def test_poll_ordering(self, active_poll, upcoming_poll, closed_poll):
        polls = list(Poll.objects.all())
        # Ordered by -start_date: upcoming has the farthest future start
        assert polls[0] == upcoming_poll
        assert polls[1] == active_poll
        assert polls[2] == closed_poll


class TestPollChoiceModel:
    def test_poll_choice_creation(self, active_poll):
        assert active_poll.choices.count() == 2

    def test_poll_choice_str(self, active_poll):
        choice = active_poll.choices.first()
        assert str(choice) == f"{active_poll.title}: {choice.text}"

    def test_poll_choice_ordering(self, active_poll):
        choices = list(active_poll.choices.all())
        assert choices[0].text == "Choice A"
        assert choices[1].text == "Choice B"


class TestPollVoteModel:
    def test_poll_vote_creation(self, active_poll, poll_user):
        choice = active_poll.choices.first()
        vote = PollVote.objects.create(poll=active_poll, choice=choice, user=poll_user)
        assert isinstance(vote, PollVote)

    def test_poll_vote_str(self, active_poll, poll_user):
        choice = active_poll.choices.first()
        vote = PollVote.objects.create(poll=active_poll, choice=choice, user=poll_user)
        assert str(vote) == f"{poll_user.username} voted on {active_poll.title}"

    def test_poll_vote_unique_per_poll(self, active_poll, poll_user):
        choice = active_poll.choices.first()
        PollVote.objects.create(poll=active_poll, choice=choice, user=poll_user)
        with pytest.raises(IntegrityError):
            PollVote.objects.create(poll=active_poll, choice=choice, user=poll_user)

    def test_poll_vote_cascade_delete_on_poll(self, active_poll, poll_user):
        choice = active_poll.choices.first()
        PollVote.objects.create(poll=active_poll, choice=choice, user=poll_user)
        poll_id = active_poll.pk
        active_poll.delete()
        assert PollVote.objects.filter(poll_id=poll_id).count() == 0

    def test_poll_vote_cascade_delete_on_choice(self, active_poll, poll_user):
        choice = active_poll.choices.first()
        PollVote.objects.create(poll=active_poll, choice=choice, user=poll_user)
        choice_id = choice.pk
        choice.delete()
        assert PollVote.objects.filter(choice_id=choice_id).count() == 0
