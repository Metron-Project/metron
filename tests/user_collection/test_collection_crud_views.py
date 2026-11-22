"""Tests for the collection list, detail, create, update and delete views."""

from datetime import UTC, datetime

from django.urls import reverse

from comicsdb.models.issue import Issue
from user_collection.models import CollectionItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403


class TestCollectionListView:
    """Tests for the CollectionListView."""

    def test_collection_list_view_requires_login(self, client):
        """Test that the view requires login."""
        url = reverse("user_collection:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_collection_list_view_authenticated(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that authenticated users see their own collection items."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert collection_item in resp.context["collection_items"]

    def test_collection_list_view_only_own_items(
        self,
        client,
        collection_user,
        other_collection_user,
        collection_item,
        collection_issue_2,
        test_password,
    ):
        """Test that users only see their own collection items."""
        # Create an item for other_collection_user
        other_item = CollectionItem.objects.create(
            user=other_collection_user,
            issue=collection_issue_2,
            quantity=1,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert collection_item in resp.context["collection_items"]
        assert other_item not in resp.context["collection_items"]

    def test_collection_list_view_empty(self, client, collection_user, test_password):
        """Test that empty collection shows correctly."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["collection_items"]) == 0

    def test_collection_list_view_pagination(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test that pagination works correctly."""
        client.login(username=collection_user.username, password=test_password)

        # Create 55 collection items

        for i in range(55):
            issue = Issue.objects.create(
                series=collection_issue_1.series,
                number=f"Test {i}",
                slug=f"test-pagination-issue-{i}",
                cover_date=collection_issue_1.cover_date,
                edited_by=collection_user,
                created_by=collection_user,
            )
            CollectionItem.objects.create(
                user=collection_user,
                issue=issue,
                quantity=1,
            )

        url = reverse("user_collection:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["collection_items"]) == 50  # paginate_by = 50


class TestCollectionDetailView:
    """Tests for the CollectionDetailView."""

    def test_collection_detail_view_requires_login(self, client, collection_item):
        """Test that the view requires login."""
        url = reverse("user_collection:detail", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_collection_detail_view_owner(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that owners can view their collection items."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:detail", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["item"] == collection_item

    def test_collection_detail_view_not_owner(
        self, client, other_collection_user, collection_item, test_password
    ):
        """Test that non-owners cannot view other users' collection items."""
        client.login(username=other_collection_user.username, password=test_password)
        url = reverse("user_collection:detail", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_collection_detail_view_with_all_fields(
        self, client, collection_user, collection_item_with_details, test_password
    ):
        """Test viewing a collection item with all optional fields populated."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:detail", kwargs={"pk": collection_item_with_details.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["item"] == collection_item_with_details


class TestCollectionCreateView:
    """Tests for the CollectionCreateView."""

    def test_collection_create_view_requires_login(self, client):
        """Test that the view requires login."""
        url = reverse("user_collection:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_collection_create_view_get(self, client, collection_user, test_password):
        """Test GET request to create view."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context

    def test_collection_create_view_post_minimal(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test POST request with minimal required fields."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_1.pk,
            "quantity": 1,
            "book_format": "PRINT",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was created
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.quantity == 1
        assert item.book_format == CollectionItem.BookFormat.PRINT

    def test_collection_create_view_post_all_fields(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test POST request with all fields."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_1.pk,
            "quantity": 2,
            "book_format": "DIGITAL",
            "purchase_date": "2023-06-15",
            "purchase_price_0": "4.99",
            "purchase_price_1": "USD",
            "purchase_store": "ComiXology",
            "storage_location": "Digital Library",
            "notes": "Sale purchase",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was created with all fields
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.quantity == 2
        assert item.book_format == "DIGITAL"
        assert str(item.purchase_date) == "2023-06-15"
        assert item.purchase_store == "ComiXology"
        assert item.storage_location == "Digital Library"
        assert item.notes == "Sale purchase"

    def test_collection_create_view_duplicate_issue(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that creating a duplicate issue shows validation error."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_item.issue.pk,
            "quantity": 1,
            "book_format": "PRINT",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_200_OK  # Form redisplayed with errors
        assert "form" in resp.context
        assert resp.context["form"].errors

    def test_collection_create_view_redirects_to_list(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test that successful creation redirects to list view."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_1.pk,
            "quantity": 1,
            "book_format": "PRINT",
        }
        resp = client.post(url, data, follow=True)
        assert resp.status_code == HTTP_200_OK
        # Should redirect to list page
        expected_url = reverse("user_collection:list")
        assert resp.redirect_chain[-1][0] == expected_url

    def test_collection_create_view_with_read_status(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test creating a collection item with read status (auto-creates read date)."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_1.pk,
            "quantity": 1,
            "book_format": "PRINT",
            "is_read": True,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was created with read status and a read date was auto-created
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.is_read is True
        assert item.date_read is not None
        assert item.read_dates.count() == 1

    def test_collection_create_view_with_is_read_without_date(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test creating a collection item marked as read (uses current date/time)."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_1.pk,
            "quantity": 1,
            "book_format": "PRINT",
            "is_read": True,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was created with read status and auto-generated date
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.is_read is True
        assert item.date_read is not None  # Auto-created with current date/time
        assert item.read_dates.count() == 1


class TestCollectionUpdateView:
    """Tests for the CollectionUpdateView."""

    def test_collection_update_view_requires_login(self, client, collection_item):
        """Test that the view requires login."""
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_collection_update_view_owner(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that owners can update their collection items."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context

    def test_collection_update_view_not_owner(
        self, client, other_collection_user, collection_item, test_password
    ):
        """Test that non-owners cannot update other users' collection items."""
        client.login(username=other_collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_collection_update_view_post(
        self, client, collection_user, collection_item, test_password
    ):
        """Test POST request to update a collection item."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        data = {
            "issue": collection_item.issue.pk,
            "quantity": 3,
            "book_format": "BOTH",
            "notes": "Updated notes",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was updated
        collection_item.refresh_from_db()
        assert collection_item.quantity == 3
        assert collection_item.book_format == "BOTH"
        assert collection_item.notes == "Updated notes"

    def test_collection_update_view_redirects_to_detail(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that successful update redirects to detail view."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        data = {
            "issue": collection_item.issue.pk,
            "quantity": 2,
            "book_format": "PRINT",
        }
        resp = client.post(url, data, follow=True)
        assert resp.status_code == HTTP_200_OK
        # Should redirect to detail page
        expected_url = reverse("user_collection:detail", kwargs={"pk": collection_item.pk})
        assert resp.redirect_chain[-1][0] == expected_url

    def test_collection_update_view_mark_as_read(
        self, client, collection_user, collection_item, test_password
    ):
        """Test updating a collection item to mark it as read (auto-creates read date)."""
        assert collection_item.is_read is False
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        data = {
            "issue": collection_item.issue.pk,
            "quantity": collection_item.quantity,
            "book_format": collection_item.book_format,
            "is_read": True,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was updated with auto-created read date
        collection_item.refresh_from_db()
        assert collection_item.is_read is True
        assert collection_item.date_read is not None
        assert collection_item.read_dates.count() == 1

    def test_collection_update_view_unmark_as_read(
        self, client, collection_user, collection_item, test_password
    ):
        """Test updating a collection item to unmark it as read."""
        # First mark it as read
        collection_item.is_read = True
        collection_item.date_read = datetime(2024, 7, 1, 12, 0, 0, tzinfo=UTC)
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        data = {
            "issue": collection_item.issue.pk,
            "quantity": collection_item.quantity,
            "book_format": collection_item.book_format,
            "is_read": False,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was updated
        collection_item.refresh_from_db()
        assert collection_item.is_read is False


class TestCollectionDeleteView:
    """Tests for the CollectionDeleteView."""

    def test_collection_delete_view_requires_login(self, client, collection_item):
        """Test that the view requires login."""
        url = reverse("user_collection:delete", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_collection_delete_view_owner(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that owners can delete their collection items."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:delete", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

    def test_collection_delete_view_not_owner(
        self, client, other_collection_user, collection_item, test_password
    ):
        """Test that non-owners cannot delete other users' collection items."""
        client.login(username=other_collection_user.username, password=test_password)
        url = reverse("user_collection:delete", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_collection_delete_view_post(
        self, client, collection_user, collection_item, test_password
    ):
        """Test POST request to delete a collection item."""
        client.login(username=collection_user.username, password=test_password)
        item_pk = collection_item.pk
        url = reverse("user_collection:delete", kwargs={"pk": item_pk})
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was deleted
        assert not CollectionItem.objects.filter(pk=item_pk).exists()

    def test_collection_delete_view_redirects_to_list(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that successful deletion redirects to list view."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:delete", kwargs={"pk": collection_item.pk})
        resp = client.post(url, follow=True)
        assert resp.status_code == HTTP_200_OK
        # Should redirect to list page
        expected_url = reverse("user_collection:list")
        assert resp.redirect_chain[-1][0] == expected_url


class TestCollectionPagination:
    """Tests for collection list pagination."""

    def test_list_view_pagination_page_1(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test that first page of pagination works correctly."""
        client.login(username=collection_user.username, password=test_password)

        # Create 55 collection items

        for i in range(55):
            issue = Issue.objects.create(
                series=collection_issue_1.series,
                number=f"Pagination {i}",
                slug=f"pagination-test-issue-{i}",
                cover_date=collection_issue_1.cover_date,
                edited_by=collection_user,
                created_by=collection_user,
            )
            CollectionItem.objects.create(
                user=collection_user,
                issue=issue,
                quantity=1,
            )

        url = reverse("user_collection:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["collection_items"]) == 50
        assert resp.context["page_obj"].number == 1
        assert resp.context["page_obj"].paginator.num_pages == 2

    def test_list_view_pagination_page_2(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test that second page of pagination works correctly."""
        client.login(username=collection_user.username, password=test_password)

        # Create 55 collection items

        for i in range(55):
            issue = Issue.objects.create(
                series=collection_issue_1.series,
                number=f"Page2 {i}",
                slug=f"page2-test-issue-{i}",
                cover_date=collection_issue_1.cover_date,
                edited_by=collection_user,
                created_by=collection_user,
            )
            CollectionItem.objects.create(
                user=collection_user,
                issue=issue,
                quantity=1,
            )

        url = reverse("user_collection:list")
        resp = client.get(url, {"page": 2})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["collection_items"]) == 5  # Remaining items
        assert resp.context["page_obj"].number == 2
