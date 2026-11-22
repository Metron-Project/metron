"""Tests for the collection statistics and missing-issues views."""

from datetime import date

from django.urls import reverse

from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from user_collection.models import CollectionItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_404_NOT_FOUND = 404


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


class TestMissingIssuesListView:
    """Tests for the MissingIssuesListView."""

    def test_missing_issues_list_requires_login(self, client):
        """Test that the view requires login."""
        url = reverse("user_collection:missing-list")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_missing_issues_list_empty(self, client, collection_user, test_password):
        """Test missing issues list with no collection."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["series_list"]) == 0

    def test_missing_issues_list_complete_series(
        self, client, collection_user, collection_series, test_password
    ):
        """Test that series with all issues owned don't appear."""
        # Create one issue and add it to collection
        issue = Issue.objects.create(
            series=collection_series,
            number="1",
            slug="complete-series-1",
            cover_date=date(2023, 1, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        CollectionItem.objects.create(user=collection_user, issue=issue)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        # Should not show the series since user has all issues
        assert len(resp.context["series_list"]) == 0

    def test_missing_issues_list_partial_series(
        self, client, collection_user, collection_series, test_password
    ):
        """Test that series with missing issues appear in list."""
        # Create 3 issues but only add 1 to collection
        issue1 = Issue.objects.create(
            series=collection_series,
            number="1",
            slug="partial-series-1",
            cover_date=date(2023, 1, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        Issue.objects.create(
            series=collection_series,
            number="2",
            slug="partial-series-2",
            cover_date=date(2023, 2, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        Issue.objects.create(
            series=collection_series,
            number="3",
            slug="partial-series-3",
            cover_date=date(2023, 3, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )

        # Only add issue 1 to collection
        CollectionItem.objects.create(user=collection_user, issue=issue1)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        series_list = resp.context["series_list"]
        assert len(series_list) == 1
        series = series_list[0]
        assert series.id == collection_series.id
        assert series.total_issues == 3
        assert series.owned_issues == 1
        assert series.missing_count == 2

    def test_missing_issues_list_multiple_series(
        self, client, collection_user, collection_publisher, single_issue_type, test_password
    ):
        """Test with multiple series having missing issues."""
        # Create two different series
        series1 = Series.objects.create(
            name="Series One",
            slug="series-one",
            publisher=collection_publisher,
            volume="1",
            year_began=2023,
            series_type=single_issue_type,
            status=Series.Status.ONGOING,
            edited_by=collection_user,
            created_by=collection_user,
        )
        series2 = Series.objects.create(
            name="Series Two",
            slug="series-two",
            publisher=collection_publisher,
            volume="1",
            year_began=2023,
            series_type=single_issue_type,
            status=Series.Status.ONGOING,
            edited_by=collection_user,
            created_by=collection_user,
        )

        # Series 1: 5 issues, own 2 (missing 3)
        for i in range(1, 6):
            issue = Issue.objects.create(
                series=series1,
                number=str(i),
                slug=f"series-one-{i}",
                cover_date=date(2023, i, 1),
                edited_by=collection_user,
                created_by=collection_user,
            )
            if i <= 2:  # Only collect first 2
                CollectionItem.objects.create(user=collection_user, issue=issue)

        # Series 2: 3 issues, own 1 (missing 2)
        for i in range(1, 4):
            issue = Issue.objects.create(
                series=series2,
                number=str(i),
                slug=f"series-two-{i}",
                cover_date=date(2023, i, 1),
                edited_by=collection_user,
                created_by=collection_user,
            )
            if i == 1:  # Only collect first one
                CollectionItem.objects.create(user=collection_user, issue=issue)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        series_list = list(resp.context["series_list"])
        assert len(series_list) == 2

        # Should be ordered by missing_count descending (3, then 2)
        assert series_list[0].id == series1.id
        assert series_list[0].missing_count == 3
        assert series_list[1].id == series2.id
        assert series_list[1].missing_count == 2

    def test_missing_issues_list_only_own_items(
        self,
        client,
        collection_user,
        other_collection_user,
        collection_series,
        test_password,
    ):
        """Test that only the authenticated user's items are considered."""
        # Create 2 issues
        issue1 = Issue.objects.create(
            series=collection_series,
            number="1",
            slug="ownership-test-1",
            cover_date=date(2023, 1, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue2 = Issue.objects.create(
            series=collection_series,
            number="2",
            slug="ownership-test-2",
            cover_date=date(2023, 2, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )

        # collection_user has issue 1
        CollectionItem.objects.create(user=collection_user, issue=issue1)

        # other_collection_user has issue 2
        CollectionItem.objects.create(user=other_collection_user, issue=issue2)

        # Login as collection_user
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        series_list = resp.context["series_list"]
        assert len(series_list) == 1
        series = series_list[0]
        # collection_user should see 1 owned (issue1), 1 missing (issue2)
        assert series.owned_issues == 1
        assert series.missing_count == 1

    def test_missing_issues_list_pagination(
        self, client, collection_user, collection_publisher, single_issue_type, test_password
    ):
        """Test that pagination works correctly."""
        client.login(username=collection_user.username, password=test_password)

        # Create 55 series, each with 2 issues, user owns 1
        for i in range(55):
            series = Series.objects.create(
                name=f"Series {i}",
                slug=f"series-{i}",
                publisher=collection_publisher,
                volume="1",
                year_began=2023,
                series_type=single_issue_type,
                status=Series.Status.ONGOING,
                edited_by=collection_user,
                created_by=collection_user,
            )
            issue1 = Issue.objects.create(
                series=series,
                number="1",
                slug=f"series-{i}-1",
                cover_date=date(2023, 1, 1),
                edited_by=collection_user,
                created_by=collection_user,
            )
            Issue.objects.create(
                series=series,
                number="2",
                slug=f"series-{i}-2",
                cover_date=date(2023, 2, 1),
                edited_by=collection_user,
                created_by=collection_user,
            )
            CollectionItem.objects.create(user=collection_user, issue=issue1)

        url = reverse("user_collection:missing-list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["series_list"]) == 50  # paginate_by = 50


class TestMissingIssuesDetailView:
    """Tests for the MissingIssuesDetailView."""

    def test_missing_issues_detail_requires_login(self, client, collection_series):
        """Test that the view requires login."""
        url = reverse("user_collection:missing-detail", kwargs={"series_id": collection_series.id})
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_missing_issues_detail_no_missing(
        self, client, collection_user, collection_series, test_password
    ):
        """Test detail view when user owns all issues."""
        # Create one issue and add it to collection
        issue = Issue.objects.create(
            series=collection_series,
            number="1",
            slug="detail-complete-1",
            cover_date=date(2023, 1, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        CollectionItem.objects.create(user=collection_user, issue=issue)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-detail", kwargs={"series_id": collection_series.id})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        # Should have no missing issues
        assert len(resp.context["missing_issues"]) == 0
        assert resp.context["total_issues"] == 1
        assert resp.context["owned_issues"] == 1
        assert resp.context["missing_count"] == 0
        assert resp.context["completion_percentage"] == 100.0

    def test_missing_issues_detail_partial_collection(
        self, client, collection_user, collection_series, test_password
    ):
        """Test detail view with missing issues."""
        # Create 5 issues, own 2
        issue1 = Issue.objects.create(
            series=collection_series,
            number="1",
            slug="detail-partial-1",
            cover_date=date(2023, 1, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue2 = Issue.objects.create(
            series=collection_series,
            number="2",
            slug="detail-partial-2",
            cover_date=date(2023, 2, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue3 = Issue.objects.create(
            series=collection_series,
            number="3",
            slug="detail-partial-3",
            cover_date=date(2023, 3, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue4 = Issue.objects.create(
            series=collection_series,
            number="4",
            slug="detail-partial-4",
            cover_date=date(2023, 4, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue5 = Issue.objects.create(
            series=collection_series,
            number="5",
            slug="detail-partial-5",
            cover_date=date(2023, 5, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )

        # Only collect issues 1 and 3
        CollectionItem.objects.create(user=collection_user, issue=issue1)
        CollectionItem.objects.create(user=collection_user, issue=issue3)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-detail", kwargs={"series_id": collection_series.id})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        missing_issues = list(resp.context["missing_issues"])
        assert len(missing_issues) == 3
        assert resp.context["total_issues"] == 5
        assert resp.context["owned_issues"] == 2
        assert resp.context["missing_count"] == 3
        assert resp.context["completion_percentage"] == 40.0

        # Check that the correct issues are missing
        missing_ids = {issue.id for issue in missing_issues}
        assert issue2.id in missing_ids
        assert issue4.id in missing_ids
        assert issue5.id in missing_ids
        assert issue1.id not in missing_ids
        assert issue3.id not in missing_ids

    def test_missing_issues_detail_invalid_series(self, client, collection_user, test_password):
        """Test detail view with non-existent series ID."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-detail", kwargs={"series_id": 99999})
        resp = client.get(url)
        assert resp.status_code == HTTP_404_NOT_FOUND

    def test_missing_issues_detail_only_user_items(
        self,
        client,
        collection_user,
        other_collection_user,
        collection_series,
        test_password,
    ):
        """Test that only the authenticated user's owned items are excluded."""
        # Create 3 issues
        issue1 = Issue.objects.create(
            series=collection_series,
            number="1",
            slug="detail-ownership-1",
            cover_date=date(2023, 1, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue2 = Issue.objects.create(
            series=collection_series,
            number="2",
            slug="detail-ownership-2",
            cover_date=date(2023, 2, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue3 = Issue.objects.create(
            series=collection_series,
            number="3",
            slug="detail-ownership-3",
            cover_date=date(2023, 3, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )

        # collection_user owns issue 1
        CollectionItem.objects.create(user=collection_user, issue=issue1)
        # other_collection_user owns issue 2
        CollectionItem.objects.create(user=other_collection_user, issue=issue2)

        # Login as collection_user
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-detail", kwargs={"series_id": collection_series.id})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        missing_issues = list(resp.context["missing_issues"])
        # Should show issues 2 and 3 as missing (even though other_user owns issue 2)
        assert len(missing_issues) == 2
        assert resp.context["owned_issues"] == 1
        missing_ids = {issue.id for issue in missing_issues}
        assert issue2.id in missing_ids
        assert issue3.id in missing_ids

    def test_missing_issues_detail_chronological_order(
        self, client, collection_user, collection_series, test_password
    ):
        """Test that missing issues are ordered by cover date and number."""
        # Create issues in non-sequential order
        issue3 = Issue.objects.create(
            series=collection_series,
            number="3",
            slug="detail-order-3",
            cover_date=date(2023, 3, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue1 = Issue.objects.create(
            series=collection_series,
            number="1",
            slug="detail-order-1",
            cover_date=date(2023, 1, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue2 = Issue.objects.create(
            series=collection_series,
            number="2",
            slug="detail-order-2",
            cover_date=date(2023, 2, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )

        # Don't collect any of them
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-detail", kwargs={"series_id": collection_series.id})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        missing_issues = list(resp.context["missing_issues"])
        # Should be ordered chronologically
        assert missing_issues[0].id == issue1.id
        assert missing_issues[1].id == issue2.id
        assert missing_issues[2].id == issue3.id

    def test_missing_issues_detail_pagination(
        self, client, collection_user, collection_series, test_password
    ):
        """Test that pagination works for missing issues."""
        client.login(username=collection_user.username, password=test_password)

        # Create 55 issues, don't collect any
        for i in range(1, 56):
            Issue.objects.create(
                series=collection_series,
                number=str(i),
                slug=f"detail-pagination-{i}",
                cover_date=date(2023, 1, i % 28 + 1) if i <= 28 else date(2023, 2, i % 28 + 1),
                edited_by=collection_user,
                created_by=collection_user,
            )

        url = reverse("user_collection:missing-detail", kwargs={"series_id": collection_series.id})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["missing_issues"]) == 50  # paginate_by = 50
        assert resp.context["total_issues"] == 55
        assert resp.context["missing_count"] == 55

    def test_missing_issues_detail_series_info(
        self, client, collection_user, collection_series, test_password
    ):
        """Test that series information is in context."""
        # Create one issue but don't collect it
        Issue.objects.create(
            series=collection_series,
            number="1",
            slug="detail-info-1",
            cover_date=date(2023, 1, 1),
            edited_by=collection_user,
            created_by=collection_user,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:missing-detail", kwargs={"series_id": collection_series.id})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        # Check series info is in context
        assert resp.context["series"] == collection_series
        assert resp.context["series"].name == collection_series.name
        assert resp.context["series"].publisher == collection_series.publisher
