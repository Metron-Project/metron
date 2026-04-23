"""Tests for polls views."""

from django.urls import reverse

from polls.models import Poll, PollVote

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_400_BAD_REQUEST = 400
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404


class TestPollListView:
    def test_list_anonymous(self, client, active_poll, upcoming_poll, closed_poll):
        url = reverse("polls:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        polls = list(resp.context["polls"])
        assert active_poll in polls
        assert upcoming_poll in polls
        assert closed_poll in polls

    def test_list_authenticated(self, client, poll_user, test_password, active_poll):
        client.login(username=poll_user.username, password=test_password)
        url = reverse("polls:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert active_poll in resp.context["polls"]

    def test_list_empty(self, client, db):
        url = reverse("polls:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["polls"]) == 0

    def test_list_active_before_closed(self, client, active_poll, closed_poll):
        url = reverse("polls:list")
        resp = client.get(url)
        polls = list(resp.context["polls"])
        assert polls.index(active_poll) < polls.index(closed_poll)


class TestPollDetailView:
    def test_detail_anonymous_active_poll(self, client, active_poll):
        url = reverse("polls:detail", args=[active_poll.pk])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["can_vote"] is False

    def test_detail_authenticated_can_vote(self, client, poll_user, test_password, active_poll):
        client.login(username=poll_user.username, password=test_password)
        url = reverse("polls:detail", args=[active_poll.pk])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["can_vote"] is True

    def test_detail_already_voted(self, client, poll_user, test_password, active_poll_with_vote):
        client.login(username=poll_user.username, password=test_password)
        url = reverse("polls:detail", args=[active_poll_with_vote.pk])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["can_vote"] is False
        assert resp.context["user_vote"] is not None

    def test_detail_upcoming_poll_cannot_vote(
        self, client, poll_user, test_password, upcoming_poll
    ):
        client.login(username=poll_user.username, password=test_password)
        url = reverse("polls:detail", args=[upcoming_poll.pk])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["can_vote"] is False

    def test_detail_closed_poll_cannot_vote(self, client, poll_user, test_password, closed_poll):
        client.login(username=poll_user.username, password=test_password)
        url = reverse("polls:detail", args=[closed_poll.pk])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["can_vote"] is False

    def test_detail_shows_choices(self, client, active_poll):
        url = reverse("polls:detail", args=[active_poll.pk])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["choices"].count() == 2

    def test_detail_total_votes_zero(self, client, active_poll):
        url = reverse("polls:detail", args=[active_poll.pk])
        resp = client.get(url)
        assert resp.context["total_votes"] == 0


class TestVoteView:
    def test_vote_anonymous_redirects(self, client, active_poll):
        choice = active_poll.choices.first()
        url = reverse("polls:vote", args=[active_poll.pk])
        resp = client.post(url, {"choice": choice.pk})
        assert resp.status_code == HTTP_302_FOUND

    def test_vote_creates_vote(self, client, poll_user, test_password, active_poll):
        client.login(username=poll_user.username, password=test_password)
        choice = active_poll.choices.first()
        url = reverse("polls:vote", args=[active_poll.pk])
        resp = client.post(url, {"choice": choice.pk})
        assert resp.status_code == HTTP_200_OK
        assert PollVote.objects.filter(poll=active_poll, user=poll_user).exists()

    def test_vote_returns_results_partial(self, client, poll_user, test_password, active_poll):
        client.login(username=poll_user.username, password=test_password)
        choice = active_poll.choices.first()
        url = reverse("polls:vote", args=[active_poll.pk])
        resp = client.post(url, {"choice": choice.pk})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["total_votes"] == 1
        assert resp.context["user_vote"].choice == choice

    def test_vote_twice_forbidden(self, client, poll_user, test_password, active_poll):
        client.login(username=poll_user.username, password=test_password)
        choice = active_poll.choices.first()
        url = reverse("polls:vote", args=[active_poll.pk])
        client.post(url, {"choice": choice.pk})
        resp = client.post(url, {"choice": choice.pk})
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_vote_on_closed_poll_forbidden(self, client, poll_user, test_password, closed_poll):
        client.login(username=poll_user.username, password=test_password)
        choice = closed_poll.choices.first()
        url = reverse("polls:vote", args=[closed_poll.pk])
        resp = client.post(url, {"choice": choice.pk})
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_vote_on_upcoming_poll_forbidden(self, client, poll_user, test_password, upcoming_poll):
        client.login(username=poll_user.username, password=test_password)
        choice = upcoming_poll.choices.first()
        url = reverse("polls:vote", args=[upcoming_poll.pk])
        resp = client.post(url, {"choice": choice.pk})
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_vote_no_choice_bad_request(self, client, poll_user, test_password, active_poll):
        client.login(username=poll_user.username, password=test_password)
        url = reverse("polls:vote", args=[active_poll.pk])
        resp = client.post(url, {})
        assert resp.status_code == HTTP_400_BAD_REQUEST

    def test_vote_choice_from_different_poll_returns_404(
        self, client, poll_user, test_password, active_poll, closed_poll
    ):
        client.login(username=poll_user.username, password=test_password)
        wrong_choice = closed_poll.choices.first()
        url = reverse("polls:vote", args=[active_poll.pk])
        resp = client.post(url, {"choice": wrong_choice.pk})
        assert resp.status_code == HTTP_404_NOT_FOUND

    def test_vote_multiple_users(
        self, client, poll_user, other_poll_user, test_password, active_poll
    ):
        choice = active_poll.choices.first()
        url = reverse("polls:vote", args=[active_poll.pk])

        client.login(username=poll_user.username, password=test_password)
        client.post(url, {"choice": choice.pk})
        client.logout()

        client.login(username=other_poll_user.username, password=test_password)
        client.post(url, {"choice": choice.pk})

        assert PollVote.objects.filter(poll=active_poll).count() == 2


class TestPollDeleteView:
    def test_delete_anonymous_redirects(self, client, active_poll):
        url = reverse("polls:delete", args=[active_poll.pk])
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND

    def test_delete_regular_user_forbidden(self, client, poll_user, test_password, active_poll):
        client.login(username=poll_user.username, password=test_password)
        url = reverse("polls:delete", args=[active_poll.pk])
        resp = client.post(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_delete_staff_can_delete(self, client, create_user, test_password, active_poll):
        staff = create_user(username="staff_deleter")
        staff.is_staff = True
        staff.save()
        client.login(username=staff.username, password=test_password)
        url = reverse("polls:delete", args=[active_poll.pk])
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND

        assert not Poll.objects.filter(pk=active_poll.pk).exists()

    def test_delete_get_shows_confirmation(self, client, create_user, test_password, active_poll):
        staff = create_user(username="staff_confirm")
        staff.is_staff = True
        staff.save()
        client.login(username=staff.username, password=test_password)
        url = reverse("polls:delete", args=[active_poll.pk])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
