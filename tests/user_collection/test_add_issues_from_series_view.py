"""Tests for adding a range of issues from a series to a collection."""

from django.urls import reverse

from comicsdb.models.issue import Issue
from user_collection.models import CollectionItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302


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

    def test_add_issues_with_digital_format(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues with DIGITAL format."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_issue_1.series.pk,
            "range_type": "all",
            "default_format": CollectionItem.BookFormat.DIGITAL,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the issue was added with DIGITAL format
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.quantity == 1
        assert item.book_format == CollectionItem.BookFormat.DIGITAL

    def test_add_issues_with_both_format(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues with BOTH format."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_issue_1.series.pk,
            "range_type": "all",
            "default_format": CollectionItem.BookFormat.BOTH,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the issue was added with BOTH format
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.quantity == 1
        assert item.book_format == CollectionItem.BookFormat.BOTH

    def test_add_issues_default_format_when_not_specified(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test that PRINT is the default format when not explicitly specified."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_issue_1.series.pk,
            "range_type": "all",
            # No default_format specified - should default to PRINT
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the issue was added with PRINT format (default)
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.quantity == 1
        assert item.book_format == CollectionItem.BookFormat.PRINT

    def test_add_issues_with_range_and_digital_format(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues with range and DIGITAL format."""
        # Create issues 1-3
        series = collection_issue_1.series
        collection_issue_1.number = "1"
        collection_issue_1.save()

        issue2 = Issue.objects.create(
            series=series,
            number="2",
            slug="test-series-digital-2",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )
        issue3 = Issue.objects.create(
            series=series,
            number="3",
            slug="test-series-digital-3",
            cover_date=collection_issue_1.cover_date,
            edited_by=collection_user,
            created_by=collection_user,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": series.pk,
            "range_type": "range",
            "start_number": "1",
            "end_number": "3",
            "default_format": CollectionItem.BookFormat.DIGITAL,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 3 issues were added with DIGITAL format
        assert CollectionItem.objects.filter(user=collection_user).count() == 3
        for issue in [collection_issue_1, issue2, issue3]:
            item = CollectionItem.objects.get(user=collection_user, issue=issue)
            assert item.book_format == CollectionItem.BookFormat.DIGITAL

    def test_add_issues_with_format_and_mark_as_read(
        self, client, collection_user, collection_issue_1, test_password
    ):
        """Test adding issues with custom format and marking them as read."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add-from-series")
        data = {
            "series": collection_issue_1.series.pk,
            "range_type": "all",
            "default_format": CollectionItem.BookFormat.BOTH,
            "mark_as_read": True,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that the issue was added with BOTH format and marked as read
        item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
        assert item.book_format == CollectionItem.BookFormat.BOTH
        assert item.is_read is True
