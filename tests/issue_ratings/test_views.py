"""Tests for issue_ratings views."""

from django.db.models import Avg
from django.urls import reverse

from issue_ratings.models import IssueRating

HTTP_200_OK = 200
HTTP_302_FOUND = 302


class TestIssueRating:
    """Test cases for issue rating functionality."""

    def test_update_rating_requires_login(self, client, rating_issue):
        """Test that rating requires authentication."""
        url = reverse("issue-ratings:rate", kwargs={"pk": rating_issue.pk})
        resp = client.post(url, data={"rating": "5"})
        assert resp.status_code == HTTP_302_FOUND
        assert "/login/" in resp.url

    def test_update_rating_set_rating(self, client, rating_issue, test_password, rating_user):
        """Test setting a rating on an issue."""
        client.login(username=rating_user.username, password=test_password)
        url = reverse("issue-ratings:rate", kwargs={"pk": rating_issue.pk})

        resp = client.post(url, data={"rating": "5"})
        assert resp.status_code == HTTP_200_OK

        rating = IssueRating.objects.filter(issue=rating_issue, user=rating_user).first()
        assert rating is not None
        assert rating.rating == 5

    def test_update_rating_updates_existing(self, client, rating_issue, test_password, rating_user):
        """Test that rating twice updates rather than duplicates the row."""
        client.login(username=rating_user.username, password=test_password)
        url = reverse("issue-ratings:rate", kwargs={"pk": rating_issue.pk})

        client.post(url, data={"rating": "2"})
        client.post(url, data={"rating": "4"})

        ratings = IssueRating.objects.filter(issue=rating_issue, user=rating_user)
        assert ratings.count() == 1
        assert ratings.first().rating == 4

    def test_update_rating_clear_rating(self, client, rating_issue, test_password, rating_user):
        """Test clearing a rating."""
        IssueRating.objects.create(issue=rating_issue, user=rating_user, rating=5)

        client.login(username=rating_user.username, password=test_password)
        url = reverse("issue-ratings:rate", kwargs={"pk": rating_issue.pk})

        resp = client.post(url, data={"rating": "0"})
        assert resp.status_code == HTTP_200_OK

        assert not IssueRating.objects.filter(issue=rating_issue, user=rating_user).exists()

    def test_update_rating_invalid_values(self, client, rating_issue, test_password, rating_user):
        """Test that invalid rating values are rejected."""
        client.login(username=rating_user.username, password=test_password)
        url = reverse("issue-ratings:rate", kwargs={"pk": rating_issue.pk})

        resp = client.post(url, data={"rating": "10"})
        assert resp.status_code == HTTP_200_OK
        assert not IssueRating.objects.filter(issue=rating_issue, user=rating_user).exists()

        resp = client.post(url, data={"rating": "-1"})
        assert resp.status_code == HTTP_200_OK
        assert not IssueRating.objects.filter(issue=rating_issue, user=rating_user).exists()

        resp = client.post(url, data={"rating": "not-a-number"})
        assert resp.status_code == HTTP_200_OK
        assert not IssueRating.objects.filter(issue=rating_issue, user=rating_user).exists()

    def test_update_rating_rejects_future_store_date(
        self, client, future_rating_issue, test_password, rating_user
    ):
        """Test that rating an issue with a future store_date is a no-op."""
        client.login(username=rating_user.username, password=test_password)
        url = reverse("issue-ratings:rate", kwargs={"pk": future_rating_issue.pk})

        resp = client.post(url, data={"rating": "5"})
        assert resp.status_code == HTTP_200_OK
        assert not IssueRating.objects.filter(issue=future_rating_issue, user=rating_user).exists()

    def test_average_rating_calculation(self, rating_issue, create_user):
        """Test that average rating is calculated correctly."""
        user1 = create_user(username="avg_user1")
        user2 = create_user(username="avg_user2")
        user3 = create_user(username="avg_user3")

        IssueRating.objects.create(issue=rating_issue, user=user1, rating=5)
        IssueRating.objects.create(issue=rating_issue, user=user2, rating=3)
        IssueRating.objects.create(issue=rating_issue, user=user3, rating=4)

        avg_rating = rating_issue.ratings.aggregate(avg=Avg("rating"))["avg"]
        assert avg_rating == 4.0
