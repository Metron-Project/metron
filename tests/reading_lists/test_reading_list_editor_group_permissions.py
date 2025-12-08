"""Tests for 'reading list editor' group managing Metron's reading lists."""

from datetime import date

from django.urls import reverse

from comicsdb.models.issue import Issue
from reading_lists.models import ReadingList, ReadingListItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404


class TestReadingListEditorGroupPermissions:
    """Tests for users in the 'reading list editor' group managing Metron's reading lists."""

    def test_editor_can_view_metron_private_list(
        self, client, reading_list_editor_user, metron_private_reading_list, test_password
    ):
        """Test that reading list editors can view Metron's private reading lists."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[metron_private_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"] == metron_private_reading_list
        assert resp.context["is_owner"]  # Editor should be treated as owner

    def test_editor_can_edit_metron_list(
        self, client, reading_list_editor_user, metron_reading_list, test_password
    ):
        """Test that reading list editors can edit Metron's reading lists."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:update", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context

        # Test POST request
        data = {
            "name": "Updated by Editor",
            "desc": "Updated description",
            "is_private": False,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        metron_reading_list.refresh_from_db()
        assert metron_reading_list.name == "Updated by Editor"

    def test_editor_can_delete_metron_list(
        self, client, reading_list_editor_user, metron_reading_list, test_password
    ):
        """Test that reading list editors can delete Metron's reading lists."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        list_id = metron_reading_list.id
        url = reverse("reading-list:delete", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        # Test POST request
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        assert not ReadingList.objects.filter(id=list_id).exists()

    def test_editor_can_add_issues_to_metron_list(
        self,
        client,
        reading_list_editor_user,
        metron_reading_list,
        reading_list_issue_1,
        test_password,
    ):
        """Test that reading list editors can add issues to Metron's reading lists."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        # Test POST request
        data = {
            "issues": [reading_list_issue_1.pk],
            "issue_order": str(reading_list_issue_1.pk),
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        assert metron_reading_list.issues.filter(id=reading_list_issue_1.id).exists()

    def test_editor_can_remove_issues_from_metron_list(
        self,
        client,
        reading_list_editor_user,
        metron_reading_list_with_issues,
        reading_list_issue_1,
        test_password,
    ):
        """Test that reading list editors can remove issues from Metron's reading lists."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        item = ReadingListItem.objects.get(
            reading_list=metron_reading_list_with_issues,
            issue=reading_list_issue_1,
        )
        url = reverse(
            "reading-list:remove-issue",
            kwargs={
                "slug": metron_reading_list_with_issues.slug,
                "item_pk": item.pk,
            },
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        # Test POST request
        item_id = item.id
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        assert not ReadingListItem.objects.filter(id=item_id).exists()

    def test_editor_can_add_issues_from_series_to_metron_list(
        self,
        client,
        reading_list_editor_user,
        metron_reading_list,
        series_with_multiple_issues,
        test_password,
    ):
        """Test that reading list editors can add issues from series to Metron's lists."""
        series, _issues = series_with_multiple_issues
        client.login(username=reading_list_editor_user.username, password=test_password)
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

    def test_editor_can_add_issues_from_arc_to_metron_list(
        self,
        client,
        reading_list_editor_user,
        metron_reading_list,
        arc_with_multiple_issues,
        test_password,
    ):
        """Test that reading list editors can add issues from arcs to Metron's lists."""
        arc, _issues = arc_with_multiple_issues
        client.login(username=reading_list_editor_user.username, password=test_password)
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

    def test_editor_cannot_edit_other_user_list(
        self, client, reading_list_editor_user, public_reading_list, test_password
    ):
        """Test that reading list editors cannot edit regular users' reading lists."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_editor_cannot_delete_other_user_list(
        self, client, reading_list_editor_user, public_reading_list, test_password
    ):
        """Test that reading list editors cannot delete regular users' reading lists."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_editor_can_see_metron_list_in_list_view(
        self, client, reading_list_editor_user, metron_private_reading_list, test_password
    ):
        """Test that reading list editors see Metron's private lists in the list view."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        # Editor should see Metron's private list
        assert metron_private_reading_list in resp.context["reading_lists"]

    def test_editor_has_owner_context_for_metron_list(
        self, client, reading_list_editor_user, metron_reading_list, test_password
    ):
        """Test that reading list editors have is_owner=True for Metron's lists."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_owner"] is True

    def test_editor_load_more_items_has_owner_true(
        self, client, reading_list_editor_user, metron_reading_list_with_issues, test_password
    ):
        """Test that editors have is_owner True in lazy load for Metron's lists."""
        # Add more issues to test pagination
        series = metron_reading_list_with_issues.reading_list_items.first().issue.series
        for i in range(4, 56):
            issue = Issue.objects.create(
                series=series,
                number=str(300 + i),  # Use higher numbers to avoid conflicts
                slug=f"editor-load-more-test-issue-{i}",
                cover_date=date(2020, (i % 12) + 1, 1),
                edited_by=reading_list_editor_user,
                created_by=reading_list_editor_user,
            )
            ReadingListItem.objects.create(
                reading_list=metron_reading_list_with_issues,
                issue=issue,
                order=i,
            )

        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:items-load-more", args=[metron_reading_list_with_issues.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_owner"] is True

    def test_editor_cannot_see_attribution_fields_in_create_form(
        self, client, reading_list_editor_user, test_password
    ):
        """Test that reading list editors don't see attribution fields (not staff)."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Attribution fields should not be in the form for non-staff users
        assert "attribution_source" not in form.fields
        assert "attribution_url" not in form.fields

    def test_editor_cannot_modify_attribution_fields_in_metron_list(
        self, client, reading_list_editor_user, metron_reading_list, test_password
    ):
        """Test that reading list editors cannot modify attribution fields (not staff)."""
        # Set initial attribution
        metron_reading_list.attribution_source = ReadingList.AttributionSource.CBRO
        metron_reading_list.attribution_url = "https://example.com/original"
        metron_reading_list.save()

        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:update", args=[metron_reading_list.slug])

        # Editor should not see attribution fields in the form
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        assert "attribution_source" not in form.fields
        assert "attribution_url" not in form.fields

        # Attempt to modify (fields will be ignored)
        data = {
            "name": "Updated by Editor",
            "desc": "Updated description",
            "is_private": False,
            "attribution_source": ReadingList.AttributionSource.CMRO,  # Will be ignored
            "attribution_url": "https://example.com/modified",  # Will be ignored
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that regular fields were updated but attribution fields were NOT
        metron_reading_list.refresh_from_db()
        assert metron_reading_list.name == "Updated by Editor"
        assert metron_reading_list.desc == "Updated description"
        # Attribution should remain unchanged
        assert metron_reading_list.attribution_source == ReadingList.AttributionSource.CBRO
        assert metron_reading_list.attribution_url == "https://example.com/original"
