"""Tests for user_collection views."""

from django.urls import reverse

from comicsdb.models.issue import Issue
from user_collection.models import CollectionItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404


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
        """Test creating a collection item with read status."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:create")
        data = {
            "issue": collection_issue_1.pk,
            "quantity": 1,
            "book_format": "PRINT",
            "is_read": True,
            "date_read": "2024-06-15",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was created with read status
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.is_read is True
        assert str(item.date_read) == "2024-06-15"

    def test_collection_create_view_with_is_read_without_date(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test creating a collection item marked as read without a date."""
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
        # Check that the item was created with read status but no date
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.is_read is True
        assert item.date_read is None


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
        """Test updating a collection item to mark it as read."""
        assert collection_item.is_read is False
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:update", kwargs={"pk": collection_item.pk})
        data = {
            "issue": collection_item.issue.pk,
            "quantity": collection_item.quantity,
            "book_format": collection_item.book_format,
            "is_read": True,
            "date_read": "2024-07-01",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was updated
        collection_item.refresh_from_db()
        assert collection_item.is_read is True
        assert str(collection_item.date_read) == "2024-07-01"

    def test_collection_update_view_unmark_as_read(
        self, client, collection_user, collection_item, test_password
    ):
        """Test updating a collection item to unmark it as read."""
        # First mark it as read
        collection_item.is_read = True
        collection_item.date_read = "2024-07-01"
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


class TestCollectionStatsView:
    """Tests for the CollectionStatsView."""

    def test_collection_stats_view_requires_login(self, client):
        """Test that the view requires login."""
        url = reverse("user_collection:stats")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_collection_stats_view_authenticated(self, client, collection_user, test_password):
        """Test that authenticated users can view their stats."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:stats")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "total_items" in resp.context
        assert "total_quantity" in resp.context
        assert "total_value" in resp.context
        assert "format_counts" in resp.context
        assert "top_series" in resp.context
        assert "read_count" in resp.context
        assert "unread_count" in resp.context

    def test_collection_stats_view_with_items(
        self, client, collection_user, collection_item, collection_item_with_details, test_password
    ):
        """Test stats calculation with multiple items."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:stats")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["total_items"] == 2
        assert resp.context["total_quantity"] == 3  # 1 + 2

    def test_collection_stats_view_empty(self, client, collection_user, test_password):
        """Test stats with empty collection."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:stats")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["total_items"] == 0
        assert resp.context["total_quantity"] == 0

    def test_collection_stats_view_format_breakdown(
        self, client, collection_user, collection_item, collection_issue_2, test_password
    ):
        """Test format breakdown in stats."""
        # Create items with different formats
        CollectionItem.objects.create(
            user=collection_user,
            issue=collection_issue_2,
            quantity=1,
            book_format=CollectionItem.BookFormat.DIGITAL,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:stats")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        format_counts = resp.context["format_counts"]
        assert len(format_counts) == 2  # PRINT and DIGITAL

        # Check that format counts are present
        formats = [fc["book_format"] for fc in format_counts]
        assert "PRINT" in formats
        assert "DIGITAL" in formats

    def test_collection_stats_view_only_user_data(
        self,
        client,
        collection_user,
        other_collection_user,
        collection_item,
        collection_issue_2,
        test_password,
    ):
        """Test that stats only include the authenticated user's data."""
        # Create item for other user
        CollectionItem.objects.create(
            user=other_collection_user,
            issue=collection_issue_2,
            quantity=10,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:stats")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        # Should only count collection_user's items
        assert resp.context["total_items"] == 1
        assert resp.context["total_quantity"] == 1

    def test_collection_stats_view_read_tracking(
        self, client, collection_user, collection_issue_1, collection_issue_2, test_password
    ):
        """Test that stats correctly count read and unread items."""
        # Create one read and one unread item
        CollectionItem.objects.create(
            user=collection_user,
            issue=collection_issue_1,
            is_read=True,
        )
        CollectionItem.objects.create(
            user=collection_user,
            issue=collection_issue_2,
            is_read=False,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:stats")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["read_count"] == 1
        assert resp.context["unread_count"] == 1
        assert resp.context["total_items"] == 2


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


class TestAddIssuesFromSeriesView:
    """Tests for the AddIssuesFromSeriesView."""

    def test_add_from_series_requires_login(self, client):
        """Test that the view requires login."""
        url = reverse("user_collection:add-from-series")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_add_from_series_get(self, client, collection_user, test_password):
        """Test GET request shows the form."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context

    def test_add_all_issues_from_series(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding all issues from a series."""

        # Create additional issues in the same series
        series = collection_issue_1.series
        issue2 = Issue.objects.create(
            series=series,
            number="2",
            slug="test-series-2023-2",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue3 = Issue.objects.create(
            series=series,
            number="3",
            slug="test-series-2023-3",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": series.pk,
            "range_type": "all",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 3 issues were added
        assert CollectionItem.objects.filter(user=collection_user).count() == 3
        assert CollectionItem.objects.filter(
            user=collection_user, issue=collection_issue_1
        ).exists()
        assert CollectionItem.objects.filter(user=collection_user, issue=issue2).exists()
        assert CollectionItem.objects.filter(user=collection_user, issue=issue3).exists()

    def test_add_issues_with_range(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues with start and end range."""

        # Create issues 1-5 in the series
        series = collection_issue_1.series
        collection_issue_1.number = "1"
        collection_issue_1.save()

        issues = [collection_issue_1]
        for i in range(2, 6):
            issue = Issue.objects.create(
                series=series,
                number=str(i),
                slug=f"test-series-2023-{i}",
                cover_date=collection_issue_1.cover_date,
                edited_by=collection_user,
                created_by=collection_user,
            )
            issues.append(issue)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": series.pk,
            "range_type": "range",
            "start_number": "2",
            "end_number": "4",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that only issues 2-4 were added
        assert CollectionItem.objects.filter(user=collection_user).count() == 3
        assert not CollectionItem.objects.filter(
            user=collection_user, issue=issues[0]
        ).exists()  # Issue 1
        assert CollectionItem.objects.filter(
            user=collection_user, issue=issues[1]
        ).exists()  # Issue 2
        assert CollectionItem.objects.filter(
            user=collection_user, issue=issues[2]
        ).exists()  # Issue 3
        assert CollectionItem.objects.filter(
            user=collection_user, issue=issues[3]
        ).exists()  # Issue 4
        assert not CollectionItem.objects.filter(
            user=collection_user, issue=issues[4]
        ).exists()  # Issue 5

    def test_add_issues_from_start_number(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues starting from a specific number."""

        # Create issues 1-3
        series = collection_issue_1.series
        collection_issue_1.number = "1"
        collection_issue_1.save()

        issue2 = Issue.objects.create(
            series=series,
            number="2",
            slug="test-series-2023-2",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue3 = Issue.objects.create(
            series=series,
            number="3",
            slug="test-series-2023-3",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": series.pk,
            "range_type": "range",
            "start_number": "2",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that issues 2-3 were added (not issue 1)
        assert CollectionItem.objects.filter(user=collection_user).count() == 2
        assert not CollectionItem.objects.filter(
            user=collection_user, issue=collection_issue_1
        ).exists()
        assert CollectionItem.objects.filter(user=collection_user, issue=issue2).exists()
        assert CollectionItem.objects.filter(user=collection_user, issue=issue3).exists()

    def test_add_issues_to_end_number(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues up to a specific number."""

        # Create issues 1-3
        series = collection_issue_1.series
        collection_issue_1.number = "1"
        collection_issue_1.save()

        issue2 = Issue.objects.create(
            series=series,
            number="2",
            slug="test-series-2023-2",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue3 = Issue.objects.create(
            series=series,
            number="3",
            slug="test-series-2023-3",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": series.pk,
            "range_type": "range",
            "end_number": "2",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that issues 1-2 were added (not issue 3)
        assert CollectionItem.objects.filter(user=collection_user).count() == 2
        assert CollectionItem.objects.filter(
            user=collection_user, issue=collection_issue_1
        ).exists()
        assert CollectionItem.objects.filter(user=collection_user, issue=issue2).exists()
        assert not CollectionItem.objects.filter(user=collection_user, issue=issue3).exists()

    def test_add_issues_skips_duplicates(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that issues already in collection are skipped."""

        # collection_item already has collection_issue_1 in the collection
        series = collection_item.issue.series
        issue2 = Issue.objects.create(
            series=series,
            number="2",
            slug="test-series-2023-2",
            cover_date=collection_item.issue.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": series.pk,
            "range_type": "all",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Should have 2 total: the existing one + the new one
        assert CollectionItem.objects.filter(user=collection_user).count() == 2
        assert CollectionItem.objects.filter(user=collection_user, issue=issue2).exists()

    def test_add_issues_default_values(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test that added issues have default values."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_issue_1.series.pk,
            "range_type": "all",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check default values
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.quantity == 1
        assert item.book_format == CollectionItem.BookFormat.PRINT

    def test_add_issues_all_duplicates_message(
        self, client, collection_user, collection_item, test_password
    ):
        """Test message when all issues are already in collection."""
        # Only one issue in the series, and it's already in collection
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_item.issue.series.pk,
            "range_type": "all",
        }
        resp = client.post(url, data, follow=True)
        assert resp.status_code == HTTP_200_OK

        # Check that info message was shown
        messages = list(resp.context["messages"])
        assert len(messages) == 1
        assert "already in your collection" in str(messages[0])

    def test_add_issues_redirects_to_list(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test that successful add redirects to collection list."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_issue_1.series.pk,
            "range_type": "all",
        }
        resp = client.post(url, data, follow=True)
        assert resp.status_code == HTTP_200_OK

        # Should redirect to list page
        expected_url = reverse("user_collection:list")
        assert resp.redirect_chain[-1][0] == expected_url

    def test_add_issues_with_mark_as_read(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues and marking them as read."""
        # Create additional issues in the same series
        series = collection_issue_1.series
        issue2 = Issue.objects.create(
            series=series,
            number="2",
            slug="test-series-mark-read-2",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue3 = Issue.objects.create(
            series=series,
            number="3",
            slug="test-series-mark-read-3",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": series.pk,
            "range_type": "all",
            "mark_as_read": True,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 3 issues were added and marked as read
        assert CollectionItem.objects.filter(user=collection_user).count() == 3
        for issue in [collection_issue_1, issue2, issue3]:
            item = CollectionItem.objects.get(user=collection_user, issue=issue)
            assert item.is_read is True

    def test_add_issues_without_mark_as_read(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues without marking them as read."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_issue_1.series.pk,
            "range_type": "all",
            "mark_as_read": False,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the issue was added but not marked as read
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.is_read is False

    def test_add_issues_mark_as_read_success_message(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test that success message indicates items were marked as read."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_issue_1.series.pk,
            "range_type": "all",
            "mark_as_read": True,
        }
        resp = client.post(url, data, follow=True)
        assert resp.status_code == HTTP_200_OK

        # Check that success message mentions "marked as read"
        messages = list(resp.context["messages"])
        assert len(messages) == 1
        assert "marked as read" in str(messages[0])


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
