"""Tests for adding issues to a reading list from a series or story arc."""

from django.urls import reverse

from reading_lists.models import ReadingListItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403


class TestAddIssuesFromSeriesView:
    """Tests for the AddIssuesFromSeriesView."""

    def test_add_issues_from_series_view_requires_login(self, client, public_reading_list):
        """Test that adding issues from series requires login."""
        url = reverse("reading-list:add-from-series", kwargs={"slug": public_reading_list.slug})
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/login/" in resp.url

    def test_add_issues_from_series_view_owner(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that owner can access the add from series view."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-series", kwargs={"slug": public_reading_list.slug})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "reading_list" in resp.context
        assert resp.context["reading_list"] == public_reading_list

    def test_add_issues_from_series_view_not_owner(
        self, client, other_user, public_reading_list, test_password
    ):
        """Test that non-owner cannot access the add from series view."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:add-from-series", kwargs={"slug": public_reading_list.slug})
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_add_all_issues_from_series_at_end(
        self,
        client,
        reading_list_user,
        public_reading_list,
        series_with_multiple_issues,
        test_password,
    ):
        """Test adding all issues from a series at the end of the reading list."""
        series, issues = series_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-series", kwargs={"slug": public_reading_list.slug})

        form_data = {
            "series": series.pk,
            "range_type": "all",
            "position": "end",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 10 issues were added
        reading_list_items = ReadingListItem.objects.filter(reading_list=public_reading_list)
        assert reading_list_items.count() == 10

        # Verify they're in the correct order
        for idx, item in enumerate(reading_list_items.order_by("order"), start=1):
            assert item.order == idx
            assert item.issue == issues[idx - 1]

    def test_add_all_issues_from_series_at_beginning(
        self,
        client,
        reading_list_user,
        reading_list_with_issues,
        series_with_multiple_issues,
        test_password,
    ):
        """Test adding all issues from a series at the beginning of an existing reading list."""
        series, issues = series_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)

        # reading_list_with_issues already has 3 issues
        initial_count = reading_list_with_issues.reading_list_items.count()
        assert initial_count == 3

        url = reverse(
            "reading-list:add-from-series", kwargs={"slug": reading_list_with_issues.slug}
        )
        form_data = {
            "series": series.pk,
            "range_type": "all",
            "position": "beginning",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 10 new issues were added + 3 existing = 13 total
        reading_list_items = ReadingListItem.objects.filter(
            reading_list=reading_list_with_issues
        ).order_by("order")
        assert reading_list_items.count() == 13

        # Verify new issues are at the beginning (orders 1-10)
        for idx in range(10):
            item = reading_list_items[idx]
            assert item.order == idx + 1
            assert item.issue == issues[idx]

        # Verify existing issues were shifted (orders 11-13)
        for idx in range(10, 13):
            item = reading_list_items[idx]
            assert item.order == idx + 1

    def test_add_issue_range_from_series(
        self,
        client,
        reading_list_user,
        public_reading_list,
        series_with_multiple_issues,
        test_password,
    ):
        """Test adding a specific range of issues from a series."""
        series, issues = series_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-series", kwargs={"slug": public_reading_list.slug})

        form_data = {
            "series": series.pk,
            "range_type": "range",
            "start_number": "3",
            "end_number": "7",
            "position": "end",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that issues 3-7 (5 issues) were added
        reading_list_items = ReadingListItem.objects.filter(reading_list=public_reading_list)
        assert reading_list_items.count() == 5

        # Verify correct issues were added
        for idx, item in enumerate(reading_list_items.order_by("order")):
            assert item.issue == issues[idx + 2]  # issues[2] is issue #3

    def test_add_issue_range_start_only(
        self,
        client,
        reading_list_user,
        public_reading_list,
        series_with_multiple_issues,
        test_password,
    ):
        """Test adding issues from a start number to the end of the series."""
        series, issues = series_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-series", kwargs={"slug": public_reading_list.slug})

        form_data = {
            "series": series.pk,
            "range_type": "range",
            "start_number": "5",
            "position": "end",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that issues 5-10 (6 issues) were added
        reading_list_items = ReadingListItem.objects.filter(reading_list=public_reading_list)
        assert reading_list_items.count() == 6

        # Verify correct issues were added
        for idx, item in enumerate(reading_list_items.order_by("order")):
            assert item.issue == issues[idx + 4]  # issues[4] is issue #5

    def test_add_issue_range_end_only(
        self,
        client,
        reading_list_user,
        public_reading_list,
        series_with_multiple_issues,
        test_password,
    ):
        """Test adding issues from the beginning to an end number."""
        series, issues = series_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-series", kwargs={"slug": public_reading_list.slug})

        form_data = {
            "series": series.pk,
            "range_type": "range",
            "end_number": "5",
            "position": "end",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that issues 1-5 (5 issues) were added
        reading_list_items = ReadingListItem.objects.filter(reading_list=public_reading_list)
        assert reading_list_items.count() == 5

        # Verify correct issues were added
        for idx, item in enumerate(reading_list_items.order_by("order")):
            assert item.issue == issues[idx]

    def test_add_issues_from_series_skips_duplicates(
        self,
        client,
        reading_list_user,
        reading_list_with_issues,
        reading_list_series,
        test_password,
    ):
        """Test that adding issues from series skips issues already in the list."""
        # reading_list_with_issues has issues 1, 2, 3 from reading_list_series
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse(
            "reading-list:add-from-series", kwargs={"slug": reading_list_with_issues.slug}
        )

        form_data = {
            "series": reading_list_series.pk,
            "range_type": "all",
            "position": "end",
        }
        resp = client.post(url, data=form_data, follow=True)
        assert resp.status_code == HTTP_200_OK

        # Should show info message that no new issues were added
        messages = list(resp.context["messages"])
        assert len(messages) > 0
        assert "No new issues to add" in str(messages[0])

        # Reading list should still have only 3 items
        assert reading_list_with_issues.reading_list_items.count() == 3

    def test_add_issues_from_series_admin_can_manage_metron_list(
        self, client, admin_user, metron_reading_list, series_with_multiple_issues, test_password
    ):
        """Test that admin can add issues to Metron's reading list."""
        series, _issues = series_with_multiple_issues
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:add-from-series", kwargs={"slug": metron_reading_list.slug})

        form_data = {
            "series": series.pk,
            "range_type": "all",
            "position": "end",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 10 issues were added
        reading_list_items = ReadingListItem.objects.filter(reading_list=metron_reading_list)
        assert reading_list_items.count() == 10

    def test_add_issues_from_series_redirects_to_detail(
        self,
        client,
        reading_list_user,
        public_reading_list,
        series_with_multiple_issues,
        test_password,
    ):
        """Test that successful addition redirects to reading list detail page."""
        series, _issues = series_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-series", kwargs={"slug": public_reading_list.slug})

        form_data = {
            "series": series.pk,
            "range_type": "all",
            "position": "end",
        }
        resp = client.post(url, data=form_data, follow=True)
        assert resp.status_code == HTTP_200_OK

        # Should redirect to detail page
        expected_url = reverse("reading-list:detail", kwargs={"slug": public_reading_list.slug})
        assert resp.redirect_chain[-1][0] == expected_url

        # Should show success message
        messages = list(resp.context["messages"])
        assert len(messages) > 0
        assert "Added" in str(messages[0])
        assert series.name in str(messages[0])


class TestAddIssuesFromArcView:
    """Tests for the AddIssuesFromArcView."""

    def test_add_issues_from_arc_view_requires_login(self, client, public_reading_list):
        """Test that adding issues from arc requires login."""
        url = reverse("reading-list:add-from-arc", kwargs={"slug": public_reading_list.slug})
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/login/" in resp.url

    def test_add_issues_from_arc_view_owner(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that owner can access the add from arc view."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-arc", kwargs={"slug": public_reading_list.slug})
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "reading_list" in resp.context
        assert resp.context["reading_list"] == public_reading_list

    def test_add_issues_from_arc_view_not_owner(
        self, client, other_user, public_reading_list, test_password
    ):
        """Test that non-owner cannot access the add from arc view."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:add-from-arc", kwargs={"slug": public_reading_list.slug})
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_add_all_issues_from_arc_at_end(
        self,
        client,
        reading_list_user,
        public_reading_list,
        arc_with_multiple_issues,
        test_password,
    ):
        """Test adding all issues from an arc at the end of the reading list."""
        arc, issues = arc_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-arc", kwargs={"slug": public_reading_list.slug})

        form_data = {
            "arc": arc.pk,
            "position": "end",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 8 issues were added
        reading_list_items = ReadingListItem.objects.filter(reading_list=public_reading_list)
        assert reading_list_items.count() == 8

        # Verify they're in the correct order (by cover date)
        for idx, item in enumerate(reading_list_items.order_by("order"), start=1):
            assert item.order == idx
            assert item.issue == issues[idx - 1]

    def test_add_all_issues_from_arc_at_beginning(
        self,
        client,
        reading_list_user,
        reading_list_with_issues,
        arc_with_multiple_issues,
        test_password,
    ):
        """Test adding all issues from an arc at the beginning of an existing reading list."""
        arc, issues = arc_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)

        # reading_list_with_issues already has 3 issues
        initial_count = reading_list_with_issues.reading_list_items.count()
        assert initial_count == 3

        url = reverse("reading-list:add-from-arc", kwargs={"slug": reading_list_with_issues.slug})
        form_data = {
            "arc": arc.pk,
            "position": "beginning",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 8 new issues were added + 3 existing = 11 total
        reading_list_items = ReadingListItem.objects.filter(
            reading_list=reading_list_with_issues
        ).order_by("order")
        assert reading_list_items.count() == 11

        # Verify new issues are at the beginning (orders 1-8)
        for idx in range(8):
            item = reading_list_items[idx]
            assert item.order == idx + 1
            assert item.issue == issues[idx]

        # Verify existing issues were shifted (orders 9-11)
        for idx in range(8, 11):
            item = reading_list_items[idx]
            assert item.order == idx + 1

    def test_add_issues_from_arc_skips_duplicates(
        self,
        client,
        reading_list_user,
        reading_list_with_issues,
        arc_with_multiple_issues,
        test_password,
    ):
        """Test that adding issues from arc skips issues already in the list."""
        arc, issues = arc_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)

        # Manually add the first 3 issues from the arc to the reading list
        for idx, issue in enumerate(issues[:3], start=4):
            ReadingListItem.objects.create(
                reading_list=reading_list_with_issues,
                issue=issue,
                order=idx,
            )

        # reading_list_with_issues now has 6 issues (3 original + 3 from arc)
        assert reading_list_with_issues.reading_list_items.count() == 6

        url = reverse("reading-list:add-from-arc", kwargs={"slug": reading_list_with_issues.slug})
        form_data = {
            "arc": arc.pk,
            "position": "end",
        }
        resp = client.post(url, data=form_data, follow=True)
        assert resp.status_code == HTTP_200_OK

        # Should add only the 5 remaining issues (8 total - 3 duplicates)
        assert reading_list_with_issues.reading_list_items.count() == 11

    def test_add_issues_from_arc_all_duplicates(
        self,
        client,
        reading_list_user,
        reading_list_with_issues,
        arc_with_multiple_issues,
        test_password,
    ):
        """Test that adding issues when all are duplicates shows info message."""
        arc, issues = arc_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)

        # Add all arc issues to the reading list first
        for idx, issue in enumerate(issues, start=4):
            ReadingListItem.objects.create(
                reading_list=reading_list_with_issues,
                issue=issue,
                order=idx,
            )

        initial_count = reading_list_with_issues.reading_list_items.count()

        url = reverse("reading-list:add-from-arc", kwargs={"slug": reading_list_with_issues.slug})
        form_data = {
            "arc": arc.pk,
            "position": "end",
        }
        resp = client.post(url, data=form_data, follow=True)
        assert resp.status_code == HTTP_200_OK

        # Should show info message that no new issues were added
        messages = list(resp.context["messages"])
        assert len(messages) > 0
        assert "No new issues to add" in str(messages[0])

        # Reading list count should not change
        assert reading_list_with_issues.reading_list_items.count() == initial_count

    def test_add_issues_from_arc_admin_can_manage_metron_list(
        self, client, admin_user, metron_reading_list, arc_with_multiple_issues, test_password
    ):
        """Test that admin can add issues to Metron's reading list."""
        arc, _issues = arc_with_multiple_issues
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:add-from-arc", kwargs={"slug": metron_reading_list.slug})

        form_data = {
            "arc": arc.pk,
            "position": "end",
        }
        resp = client.post(url, data=form_data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all 8 issues were added
        reading_list_items = ReadingListItem.objects.filter(reading_list=metron_reading_list)
        assert reading_list_items.count() == 8

    def test_add_issues_from_arc_redirects_to_detail(
        self,
        client,
        reading_list_user,
        public_reading_list,
        arc_with_multiple_issues,
        test_password,
    ):
        """Test that successful addition redirects to reading list detail page."""
        arc, _issues = arc_with_multiple_issues
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-from-arc", kwargs={"slug": public_reading_list.slug})

        form_data = {
            "arc": arc.pk,
            "position": "end",
        }
        resp = client.post(url, data=form_data, follow=True)
        assert resp.status_code == HTTP_200_OK

        # Should redirect to detail page
        expected_url = reverse("reading-list:detail", kwargs={"slug": public_reading_list.slug})
        assert resp.redirect_chain[-1][0] == expected_url

        # Should show success message
        messages = list(resp.context["messages"])
        assert len(messages) > 0
        assert "Added" in str(messages[0])
        assert arc.name in str(messages[0])
