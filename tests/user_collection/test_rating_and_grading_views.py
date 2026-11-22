"""Tests for collection item rating and grading."""

from decimal import Decimal

from django.urls import reverse

from issue_ratings.models import IssueRating
from user_collection.models import CollectionItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_404_NOT_FOUND = 404


class TestUpdateRatingView:
    """Tests for the update_rating HTMX view."""

    def test_update_rating_requires_login(self, client, collection_item):
        """Test that the view requires login."""
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": "3"})
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_update_rating_set_rating(
        self, client, collection_user, collection_item, test_password
    ):
        """Test setting a rating (1-5)."""
        client.login(username=collection_user.username, password=test_password)
        assert collection_item.rating is None

        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": "3"})
        assert resp.status_code == HTTP_200_OK

        # Check that the rating was updated
        collection_item.refresh_from_db()
        assert collection_item.rating == 3

    def test_update_rating_syncs_to_issue_rating(
        self, client, collection_user, collection_item, test_password
    ):
        """Rating a collection item through the HTMX endpoint syncs the community IssueRating."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})

        client.post(url, {"rating": "4"})
        rating = IssueRating.objects.get(issue=collection_item.issue, user=collection_user)
        assert rating.rating == 4

        client.post(url, {"rating": "0"})
        assert not IssueRating.objects.filter(
            issue=collection_item.issue, user=collection_user
        ).exists()

    def test_update_rating_all_valid_values(
        self, client, collection_user, collection_item, test_password
    ):
        """Test all valid rating values from 1 to 5."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})

        for rating_value in range(1, 6):
            resp = client.post(url, {"rating": str(rating_value)})
            assert resp.status_code == HTTP_200_OK

            collection_item.refresh_from_db()
            assert collection_item.rating == rating_value

    def test_update_rating_clear_rating(
        self, client, collection_user, collection_item, test_password
    ):
        """Test clearing a rating by sending 0."""
        # First set a rating
        collection_item.rating = 3
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": "0"})
        assert resp.status_code == HTTP_200_OK

        # Check that the rating was cleared
        collection_item.refresh_from_db()
        assert collection_item.rating is None

    def test_update_rating_invalid_high_value(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that ratings above 5 are rejected."""
        collection_item.rating = 3
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": "6"})
        assert resp.status_code == HTTP_200_OK

        # Rating should not have changed
        collection_item.refresh_from_db()
        assert collection_item.rating == 3

    def test_update_rating_invalid_low_value(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that ratings below 1 (except 0) are rejected."""
        collection_item.rating = 3
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": "-1"})
        assert resp.status_code == HTTP_200_OK

        # Rating should not have changed
        collection_item.refresh_from_db()
        assert collection_item.rating == 3

    def test_update_rating_not_owner(
        self, client, other_collection_user, collection_item, test_password
    ):
        """Test that non-owners cannot rate other users' items."""
        client.login(username=other_collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": "4"})
        assert resp.status_code == HTTP_404_NOT_FOUND

        # Rating should not have been set
        collection_item.refresh_from_db()
        assert collection_item.rating is None

    def test_update_rating_returns_template(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that the view returns the star rating template."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": "4"})

        assert resp.status_code == HTTP_200_OK
        # Check that it's returning the partial template
        assert "star-rating" in resp.content.decode()

    def test_update_rating_change_existing(
        self, client, collection_user, collection_item, test_password
    ):
        """Test changing an existing rating."""
        # Set initial rating
        collection_item.rating = 2
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})

        # Change to 4
        resp = client.post(url, {"rating": "4"})
        assert resp.status_code == HTTP_200_OK

        collection_item.refresh_from_db()
        assert collection_item.rating == 4

        # Change to 1
        resp = client.post(url, {"rating": "1"})
        assert resp.status_code == HTTP_200_OK

        collection_item.refresh_from_db()
        assert collection_item.rating == 1

    def test_update_rating_invalid_string(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that non-numeric rating values are rejected."""
        collection_item.rating = 3
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": "abc"})
        assert resp.status_code == HTTP_200_OK

        # Rating should not have changed
        collection_item.refresh_from_db()
        assert collection_item.rating == 3

    def test_update_rating_empty_value(
        self, client, collection_user, collection_item, test_password
    ):
        """Test sending empty rating value."""
        collection_item.rating = 3
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {"rating": ""})
        assert resp.status_code == HTTP_200_OK

        # Rating should not have changed
        collection_item.refresh_from_db()
        assert collection_item.rating == 3

    def test_update_rating_no_rating_parameter(
        self, client, collection_user, collection_item, test_password
    ):
        """Test POST without rating parameter."""
        collection_item.rating = 3
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:rate", kwargs={"pk": collection_item.pk})
        resp = client.post(url, {})
        assert resp.status_code == HTTP_200_OK

        # Rating should not have changed
        collection_item.refresh_from_db()
        assert collection_item.rating == 3


class TestCollectionGradingViews:
    """Tests for collection grading functionality in views."""

    def test_collection_detail_view_with_professional_grade(
        self, client, collection_user, collection_item_professionally_graded, test_password
    ):
        """Test that professionally graded items display correctly."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse(
            "user_collection:detail", kwargs={"pk": collection_item_professionally_graded.pk}
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        content = resp.content.decode()
        # Check that grading information box is present
        assert "Grading Information" in content
        # Check that grade is displayed
        assert "9.8 (NM/M - Near Mint/Mint)" in content
        # Check that grading company is displayed
        assert "CGC (Certified Guaranty Company)" in content
        # Check for professional grading indicator
        assert "Professionally graded" in content

    def test_collection_detail_view_with_user_assessed_grade(
        self, client, collection_user, collection_item_user_graded, test_password
    ):
        """Test that user-assessed graded items display correctly."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:detail", kwargs={"pk": collection_item_user_graded.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        content = resp.content.decode()
        # Check that grading information box is present
        assert "Grading Information" in content
        # Check that grade is displayed
        assert "8.5 (VF+ - Very Fine+)" in content
        # Check for user-assessed indicator
        assert "User-assessed grade" in content

    def test_collection_detail_view_without_grade(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that items without grades don't show grading section."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:detail", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        content = resp.content.decode()
        # Grading Information box should not be present
        assert "Grading Information" not in content

    def test_collection_create_view_with_professional_grade(
        self, client, collection_user, collection_issue_2, test_password
    ):
        """Test creating a collection item with a professional grade."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_2.pk,
            "quantity": 1,
            "book_format": "PRINT",
            "grade": str(Decimal("9.8")),
            "grading_company": "CGC",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the item was created with grade and company
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_2)
        assert item.grade == Decimal("9.8")
        assert item.grading_company == "CGC"

    def test_collection_create_view_with_user_assessed_grade(
        self, client, collection_user, collection_issue_2, test_password
    ):
        """Test creating a collection item with a user-assessed grade."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_2.pk,
            "quantity": 1,
            "book_format": "PRINT",
            "grade": str(Decimal("8.0")),
            # No grading_company = user-assessed
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the item was created with grade but no company
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_2)
        assert item.grade == Decimal("8.0")
        assert item.grading_company == ""

    def test_collection_create_view_without_grade(
        self, client, collection_user, collection_issue_2, test_password
    ):
        """Test creating a collection item without a grade."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_2.pk,
            "quantity": 1,
            "book_format": "PRINT",
            # No grade or grading_company
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the item was created without grade
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_2)
        assert item.grade is None
        assert item.grading_company == ""

    def test_collection_update_view_add_grade(
        self, client, collection_user, collection_item, test_password
    ):
        """Test updating a collection item to add a grade."""
        assert collection_item.grade is None
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        data = {
            "issue": collection_item.issue.pk,
            "quantity": collection_item.quantity,
            "book_format": collection_item.book_format,
            "grade": str(Decimal("9.4")),
            "grading_company": "CBCS",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the grade was added
        collection_item.refresh_from_db()
        assert collection_item.grade == Decimal("9.4")
        assert collection_item.grading_company == "CBCS"

    def test_collection_update_view_change_grade(
        self, client, collection_user, collection_item_professionally_graded, test_password
    ):
        """Test updating a graded collection item to change the grade."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse(
            "user_collection:update", kwargs={"pk": collection_item_professionally_graded.pk}
        )
        data = {
            "issue": collection_item_professionally_graded.issue.pk,
            "quantity": collection_item_professionally_graded.quantity,
            "book_format": collection_item_professionally_graded.book_format,
            "grade": str(Decimal("9.6")),  # Changed from 9.8
            "grading_company": "PGX",  # Changed from CGC
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the grade was updated
        collection_item_professionally_graded.refresh_from_db()
        assert collection_item_professionally_graded.grade == Decimal("9.6")
        assert collection_item_professionally_graded.grading_company == "PGX"

    def test_collection_update_view_remove_grade(
        self, client, collection_user, collection_item_user_graded, test_password
    ):
        """Test updating a collection item to remove the grade."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item_user_graded.pk})
        data = {
            "issue": collection_item_user_graded.issue.pk,
            "quantity": collection_item_user_graded.quantity,
            "book_format": collection_item_user_graded.book_format,
            # No grade or grading_company = remove them
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the grade was removed
        collection_item_user_graded.refresh_from_db()
        assert collection_item_user_graded.grade is None
        assert collection_item_user_graded.grading_company == ""

    def test_collection_list_view_with_graded_items(
        self, client, collection_user, collection_item_professionally_graded, test_password
    ):
        """Test that graded items appear in the collection list."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        # Check that the graded item is in the list
        assert collection_item_professionally_graded in resp.context["collection_items"]

        content = resp.content.decode()
        # Check that grade column shows the value
        assert "9.8" in content
