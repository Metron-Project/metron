"""Tests for reading list ratings and per-item issue type editing."""

from django.db.models import Avg
from django.urls import reverse

from reading_lists.models import ReadingList, ReadingListItem, ReadingListRating

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403


class TestReadingListRating:
    """Test cases for reading list rating functionality."""

    def test_update_rating_requires_login(self, client, public_reading_list):
        """Test that rating requires authentication."""
        url = reverse("reading-list:rate", kwargs={"slug": public_reading_list.slug})
        resp = client.post(url, data={"rating": "5"})
        assert resp.status_code == HTTP_302_FOUND
        assert "/login/" in resp.url

    def test_update_rating_set_rating(
        self, client, public_reading_list, test_password, create_user
    ):
        """Test setting a rating on a public reading list."""

        # Create a different user to rate the list
        other_user = create_user(username="rater_user")
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:rate", kwargs={"slug": public_reading_list.slug})

        # Ensure the reading list belongs to a different user
        assert public_reading_list.user != other_user

        resp = client.post(url, data={"rating": "5"})
        assert resp.status_code == HTTP_200_OK

        # Check rating was created
        rating = ReadingListRating.objects.filter(
            reading_list=public_reading_list, user=other_user
        ).first()
        assert rating is not None
        assert rating.rating == 5

    def test_update_rating_clear_rating(
        self, client, public_reading_list, test_password, create_user
    ):
        """Test clearing a rating."""
        # Create a different user to rate the list
        other_user = create_user(username="rater_user2")
        # Create a rating first
        ReadingListRating.objects.create(
            reading_list=public_reading_list, user=other_user, rating=5
        )

        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:rate", kwargs={"slug": public_reading_list.slug})

        resp = client.post(url, data={"rating": "0"})
        assert resp.status_code == HTTP_200_OK

        # Check rating was deleted
        rating_exists = ReadingListRating.objects.filter(
            reading_list=public_reading_list, user=other_user
        ).exists()
        assert not rating_exists

    def test_update_rating_invalid_values(
        self, client, public_reading_list, test_password, create_user
    ):
        """Test that invalid rating values are rejected."""
        # Create a different user to rate the list
        other_user = create_user(username="rater_user3")
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:rate", kwargs={"slug": public_reading_list.slug})

        # Test value too high
        resp = client.post(url, data={"rating": "10"})
        assert resp.status_code == HTTP_200_OK
        assert not ReadingListRating.objects.filter(
            reading_list=public_reading_list, user=other_user
        ).exists()

        # Test negative value
        resp = client.post(url, data={"rating": "-1"})
        assert resp.status_code == HTTP_200_OK
        assert not ReadingListRating.objects.filter(
            reading_list=public_reading_list, user=other_user
        ).exists()

    def test_update_rating_private_list_forbidden(
        self, client, reading_list_user, private_reading_list, test_password
    ):
        """Test that private lists cannot be rated."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:rate", kwargs={"slug": private_reading_list.slug})

        resp = client.post(url, data={"rating": "5"})
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_update_rating_own_list_forbidden(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that users cannot rate their own reading lists."""
        # Make sure the reading list belongs to the user
        public_reading_list.user = reading_list_user
        public_reading_list.save()

        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:rate", kwargs={"slug": public_reading_list.slug})

        resp = client.post(url, data={"rating": "5"})
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_average_rating_calculation(self, create_user):
        """Test that average rating is calculated correctly."""
        # Create a list owner
        owner = create_user(username="list_owner")
        reading_list = ReadingList.objects.create(user=owner, name="Test List", is_private=False)

        # Create multiple ratings from different users
        user1 = create_user(username="user1")
        user2 = create_user(username="user2")
        user3 = create_user(username="user3")

        ReadingListRating.objects.create(reading_list=reading_list, user=user1, rating=5)
        ReadingListRating.objects.create(reading_list=reading_list, user=user2, rating=3)
        ReadingListRating.objects.create(reading_list=reading_list, user=user3, rating=4)

        # Calculate average
        avg_rating = reading_list.ratings.aggregate(avg=Avg("rating"))["avg"]
        assert avg_rating == 4.0


class TestIssueTypeEditing:
    """Test cases for editing issue types in reading lists."""

    def test_edit_issue_type_requires_login(self, client, reading_list_with_issues):
        """Test that editing issue type requires authentication."""
        item = reading_list_with_issues.reading_list_items.first()
        url = reverse(
            "reading-list:edit-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/login/" in resp.url

    def test_edit_issue_type_requires_ownership(
        self, client, reading_list_with_issues, other_user, test_password
    ):
        """Test that only the owner can edit issue types."""
        client.login(username=other_user.username, password=test_password)
        item = reading_list_with_issues.reading_list_items.first()
        url = reverse(
            "reading-list:edit-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_edit_issue_type_owner_success(
        self, client, reading_list_with_issues, reading_list_user, test_password
    ):
        """Test that owner can view the edit form."""
        client.login(username=reading_list_user.username, password=test_password)
        item = reading_list_with_issues.reading_list_items.first()
        url = reverse(
            "reading-list:edit-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert b"issue_type" in resp.content

    def test_update_issue_type_set_type(
        self, client, reading_list_with_issues, reading_list_user, test_password
    ):
        """Test setting an issue type."""
        client.login(username=reading_list_user.username, password=test_password)
        item = reading_list_with_issues.reading_list_items.first()
        assert item.issue_type == ""  # Initially empty

        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.post(url, data={"issue_type": "CORE"})
        assert resp.status_code == HTTP_200_OK

        # Refresh from database
        item.refresh_from_db()
        assert item.issue_type == "CORE"

    def test_update_issue_type_clear_type(
        self, client, reading_list_with_issues, reading_list_user, test_password
    ):
        """Test clearing an issue type."""
        client.login(username=reading_list_user.username, password=test_password)
        item = reading_list_with_issues.reading_list_items.first()
        item.issue_type = "PROLOGUE"
        item.save()

        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.post(url, data={"issue_type": ""})
        assert resp.status_code == HTTP_200_OK

        # Refresh from database
        item.refresh_from_db()
        assert item.issue_type == ""

    def test_update_issue_type_all_types(
        self, client, reading_list_with_issues, reading_list_user, test_password
    ):
        """Test all valid issue types."""
        client.login(username=reading_list_user.username, password=test_password)
        item = reading_list_with_issues.reading_list_items.first()
        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )

        valid_types = ["PROLOGUE", "CORE", "TIE_IN", "EPILOGUE"]
        for issue_type in valid_types:
            resp = client.post(url, data={"issue_type": issue_type})
            assert resp.status_code == HTTP_200_OK
            item.refresh_from_db()
            assert item.issue_type == issue_type

    def test_update_issue_type_invalid_value(
        self, client, reading_list_with_issues, reading_list_user, test_password
    ):
        """Test that invalid issue types are rejected."""
        client.login(username=reading_list_user.username, password=test_password)
        item = reading_list_with_issues.reading_list_items.first()
        original_type = item.issue_type

        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.post(url, data={"issue_type": "INVALID"})
        assert resp.status_code == HTTP_200_OK

        # Value should not have changed
        item.refresh_from_db()
        assert item.issue_type == original_type

    def test_update_issue_type_requires_login(self, client, reading_list_with_issues):
        """Test that updating requires authentication."""
        item = reading_list_with_issues.reading_list_items.first()
        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.post(url, data={"issue_type": "CORE"})
        assert resp.status_code == HTTP_302_FOUND
        assert "/login/" in resp.url

    def test_update_issue_type_requires_ownership(
        self, client, reading_list_with_issues, other_user, test_password
    ):
        """Test that only owner can update issue types."""
        client.login(username=other_user.username, password=test_password)
        item = reading_list_with_issues.reading_list_items.first()
        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.post(url, data={"issue_type": "CORE"})
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_cancel_edit_issue_type(
        self, client, reading_list_with_issues, reading_list_user, test_password
    ):
        """Test canceling the edit returns to display mode."""
        client.login(username=reading_list_user.username, password=test_password)
        item = reading_list_with_issues.reading_list_items.first()
        item.issue_type = "CORE"
        item.save()

        url = reverse(
            "reading-list:cancel-edit-issue-type",
            kwargs={"slug": reading_list_with_issues.slug, "item_pk": item.pk},
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        # Should show the display template, not edit template
        assert b"Core Issue" in resp.content  # Display of issue type
        assert b'name="issue_type"' not in resp.content  # No form field

    def test_admin_can_edit_metron_list_issue_type(
        self, client, admin_user, metron_reading_list, reading_list_issue_1, test_password
    ):
        """Test that admin can edit issue types on Metron lists."""
        # Add an issue to the Metron list
        item = ReadingListItem.objects.create(
            reading_list=metron_reading_list, issue=reading_list_issue_1, order=1
        )

        client.login(username=admin_user.username, password=test_password)
        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": metron_reading_list.slug, "item_pk": item.pk},
        )
        resp = client.post(url, data={"issue_type": "CORE"})
        assert resp.status_code == HTTP_200_OK

        item.refresh_from_db()
        assert item.issue_type == "CORE"

    def test_editor_can_edit_metron_list_issue_type(
        self,
        client,
        reading_list_editor_user,
        metron_reading_list,
        reading_list_issue_1,
        test_password,
    ):
        """Test that reading list editors can edit issue types on Metron lists."""
        # Add an issue to the Metron list
        item = ReadingListItem.objects.create(
            reading_list=metron_reading_list, issue=reading_list_issue_1, order=1
        )

        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": metron_reading_list.slug, "item_pk": item.pk},
        )
        resp = client.post(url, data={"issue_type": "PROLOGUE"})
        assert resp.status_code == HTTP_200_OK

        item.refresh_from_db()
        assert item.issue_type == "PROLOGUE"

    def test_regular_user_cannot_edit_metron_list_issue_type(
        self, client, metron_reading_list, reading_list_issue_1, create_user, test_password
    ):
        """Test that regular users cannot edit issue types on Metron lists."""
        regular_user = create_user(username="regular_user")
        # Add an issue to the Metron list
        item = ReadingListItem.objects.create(
            reading_list=metron_reading_list, issue=reading_list_issue_1, order=1
        )

        client.login(username=regular_user.username, password=test_password)
        url = reverse(
            "reading-list:update-issue-type",
            kwargs={"slug": metron_reading_list.slug, "item_pk": item.pk},
        )
        resp = client.post(url, data={"issue_type": "CORE"})
        assert resp.status_code == HTTP_403_FORBIDDEN
