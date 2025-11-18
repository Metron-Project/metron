"""Tests for admin users managing Metron's reading lists."""

from django.urls import reverse

from reading_lists.models import ReadingList, ReadingListItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404


class TestAdminMetronPermissions:
    """Tests for admin users managing Metron's reading lists."""

    def test_admin_can_view_metron_private_list(
        self, client, admin_user, metron_private_reading_list, test_password
    ):
        """Test that admin users can view Metron's private reading lists."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[metron_private_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"] == metron_private_reading_list
        assert resp.context["is_owner"]  # Admin should be treated as owner

    def test_admin_can_edit_metron_list(
        self, client, admin_user, metron_reading_list, test_password
    ):
        """Test that admin users can edit Metron's reading lists."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:update", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context

        # Test POST request
        data = {
            "name": "Updated by Admin",
            "desc": "Updated description",
            "is_private": False,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        metron_reading_list.refresh_from_db()
        assert metron_reading_list.name == "Updated by Admin"

    def test_admin_can_delete_metron_list(
        self, client, admin_user, metron_reading_list, test_password
    ):
        """Test that admin users can delete Metron's reading lists."""
        client.login(username=admin_user.username, password=test_password)
        list_id = metron_reading_list.id
        url = reverse("reading-list:delete", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

        # Test POST request
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        assert not ReadingList.objects.filter(id=list_id).exists()

    def test_admin_can_add_issues_to_metron_list(
        self,
        client,
        admin_user,
        metron_reading_list,
        reading_list_issue_1,
        test_password,
    ):
        """Test that admin users can add issues to Metron's reading lists."""
        client.login(username=admin_user.username, password=test_password)
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

    def test_admin_can_remove_issues_from_metron_list(
        self,
        client,
        admin_user,
        metron_reading_list_with_issues,
        reading_list_issue_1,
        test_password,
    ):
        """Test that admin users can remove issues from Metron's reading lists."""
        client.login(username=admin_user.username, password=test_password)
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

    def test_regular_user_cannot_edit_metron_list(
        self, client, reading_list_user, metron_reading_list, test_password
    ):
        """Test that regular users cannot edit Metron's reading lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_regular_user_cannot_delete_metron_list(
        self, client, reading_list_user, metron_reading_list, test_password
    ):
        """Test that regular users cannot delete Metron's reading lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:delete", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_regular_user_cannot_add_issues_to_metron_list(
        self, client, reading_list_user, metron_reading_list, test_password
    ):
        """Test that regular users cannot add issues to Metron's reading lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_regular_user_cannot_remove_issues_from_metron_list(
        self,
        client,
        reading_list_user,
        metron_reading_list_with_issues,
        reading_list_issue_1,
        test_password,
    ):
        """Test that regular users cannot remove issues from Metron's reading lists."""
        client.login(username=reading_list_user.username, password=test_password)
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
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_admin_cannot_edit_other_user_list(
        self, client, admin_user, public_reading_list, test_password
    ):
        """Test that admin users cannot edit regular users' reading lists."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_regular_user_cannot_see_metron_private_list(
        self, client, reading_list_user, metron_private_reading_list, test_password
    ):
        """Test that regular users cannot see Metron's private lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[metron_private_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_404_NOT_FOUND

    def test_admin_can_see_metron_list_in_list_view(
        self, client, admin_user, metron_private_reading_list, test_password
    ):
        """Test that admin users see Metron's private lists in the list view."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        # Admin should see Metron's private list
        assert metron_private_reading_list in resp.context["reading_lists"]

    def test_regular_user_cannot_see_metron_private_list_in_list_view(
        self, client, reading_list_user, metron_private_reading_list, test_password
    ):
        """Test that regular users don't see Metron's private lists in the list view."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        # Regular user should not see Metron's private list
        assert metron_private_reading_list not in resp.context["reading_lists"]
