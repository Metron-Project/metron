"""Tests for reading_lists views."""

import time
from datetime import date

import pytest
from django.urls import reverse

from comicsdb.models.issue import Issue
from reading_lists.models import ReadingList, ReadingListItem
from users.models import CustomUser

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404


class TestReadingListListView:
    """Tests for the ReadingListListView."""

    def test_reading_list_list_view_anonymous(
        self, client, public_reading_list, private_reading_list
    ):
        """Test that anonymous users can view public reading lists."""
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert public_reading_list in resp.context["reading_lists"]
        # Private lists should not be visible to anonymous users
        assert private_reading_list not in resp.context["reading_lists"]

    def test_reading_list_list_view_authenticated(
        self, client, reading_list_user, public_reading_list, private_reading_list, test_password
    ):
        """Test that authenticated users see public lists and their own private lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert public_reading_list in resp.context["reading_lists"]
        assert private_reading_list in resp.context["reading_lists"]

    def test_reading_list_list_view_other_user_private(
        self, client, other_user, private_reading_list, test_password
    ):
        """Test that users cannot see other users' private lists."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert private_reading_list not in resp.context["reading_lists"]

    def test_reading_list_list_view_pagination(self, client, reading_list_user, test_password):
        """Test that pagination works correctly."""
        # Log in first
        client.login(username=reading_list_user.username, password=test_password)
        # Create 35 reading lists
        for i in range(35):
            ReadingList.objects.create(
                user=reading_list_user,
                name=f"List {i}",
            )
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["reading_lists"]) == 30  # paginate_by = 30


class TestSearchReadingListListView:
    """Tests for the SearchReadingListListView."""

    def test_search_reading_list_anonymous(self, client, public_reading_list, private_reading_list):
        """Test that anonymous users can search public reading lists."""
        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "Public"})
        assert resp.status_code == HTTP_200_OK
        assert public_reading_list in resp.context["reading_lists"]
        # Private lists should not appear in search results for anonymous users
        assert private_reading_list not in resp.context["reading_lists"]

    def test_search_reading_list_by_name(
        self, client, reading_list_user, public_reading_list, private_reading_list, test_password
    ):
        """Test searching reading lists by name."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "Public"})
        assert resp.status_code == HTTP_200_OK
        assert public_reading_list in resp.context["reading_lists"]
        assert private_reading_list not in resp.context["reading_lists"]

    def test_search_reading_list_by_username(
        self, client, reading_list_user, other_user_reading_list, public_reading_list, test_password
    ):
        """Test searching reading lists by username."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "other_user"})
        assert resp.status_code == HTTP_200_OK
        assert other_user_reading_list in resp.context["reading_lists"]
        assert public_reading_list not in resp.context["reading_lists"]

    def test_search_reading_list_by_attribution_source(
        self,
        client,
        reading_list_user,
        reading_list_with_issues,
        public_reading_list,
        test_password,
    ):
        """Test searching reading lists by attribution source."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "CBRO"})
        assert resp.status_code == HTTP_200_OK
        assert reading_list_with_issues in resp.context["reading_lists"]
        assert public_reading_list not in resp.context["reading_lists"]

    def test_search_reading_list_no_results(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test searching with no matching results."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "nonexistent"})
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["reading_lists"]) == 0

    def test_search_reading_list_respects_privacy(
        self, client, reading_list_user, private_reading_list, test_password
    ):
        """Test that search respects privacy settings for authenticated users."""
        # Log in as a different user who shouldn't see the private list

        other_user = CustomUser.objects.create_user(
            username="different_user", email="different@example.com", password=test_password
        )
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "Private"})
        assert resp.status_code == HTTP_200_OK
        assert private_reading_list not in resp.context["reading_lists"]

    def test_search_reading_list_authenticated_sees_own_private(
        self, client, reading_list_user, private_reading_list, test_password
    ):
        """Test that authenticated users can search their own private lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "Private"})
        assert resp.status_code == HTTP_200_OK
        assert private_reading_list in resp.context["reading_lists"]


class TestUserReadingListListView:
    """Tests for the UserReadingListListView."""

    def test_user_reading_list_list_view_requires_login(self, client):
        """Test that the view requires login."""
        url = reverse("reading-list:my-lists")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_user_reading_list_list_view(
        self, client, reading_list_user, public_reading_list, private_reading_list, test_password
    ):
        """Test that users only see their own lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:my-lists")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert public_reading_list in resp.context["reading_lists"]
        assert private_reading_list in resp.context["reading_lists"]

    def test_user_reading_list_list_view_not_other_users(
        self, client, other_user, public_reading_list, test_password
    ):
        """Test that users don't see other users' lists."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:my-lists")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert public_reading_list not in resp.context["reading_lists"]


class TestReadingListDetailView:
    """Tests for the ReadingListDetailView."""

    def test_reading_list_detail_view_anonymous_public(self, client, public_reading_list):
        """Test that anonymous users can view public reading lists."""
        url = reverse("reading-list:detail", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"] == public_reading_list

    def test_reading_list_detail_view_public(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test viewing a public reading list."""
        # Create and log in as a different user to test viewing someone else's public list

        other_user = CustomUser.objects.create_user(
            username="viewer_user", email="viewer@example.com", password=test_password
        )
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"] == public_reading_list
        # User is viewing someone else's public list
        assert not resp.context["is_owner"]

    def test_reading_list_detail_view_private_anonymous(self, client, private_reading_list):
        """Test that anonymous users cannot view private reading lists."""
        url = reverse("reading-list:detail", args=[private_reading_list.slug])
        resp = client.get(url)
        # Private lists are filtered out for anonymous users, resulting in 404
        assert resp.status_code == HTTP_404_NOT_FOUND

    def test_reading_list_detail_view_private_owner(
        self, client, reading_list_user, private_reading_list, test_password
    ):
        """Test that owners can view their private lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[private_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"] == private_reading_list
        assert resp.context["is_owner"]

    def test_reading_list_detail_view_private_other_user(
        self, client, other_user, private_reading_list, test_password
    ):
        """Test that other users cannot view private lists."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[private_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_404_NOT_FOUND

    def test_reading_list_detail_view_with_issues(
        self, client, reading_list_user, reading_list_with_issues, test_password
    ):
        """Test viewing a reading list with issues."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[reading_list_with_issues.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["reading_list_items"]) == 3


class TestReadingListCreateView:
    """Tests for the ReadingListCreateView."""

    def test_reading_list_create_view_requires_login(self, client):
        """Test that the view requires login."""
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_reading_list_create_view_get(self, client, reading_list_user, test_password):
        """Test GET request to create view."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context
        assert resp.context["title"] == "Create Reading List"
        assert resp.context["button_text"] == "Create"

    def test_reading_list_create_view_post(self, client, reading_list_user, test_password):
        """Test POST request to create a reading list."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:create")
        data = {
            "name": "New Reading List",
            "desc": "A new reading list",
            "is_private": False,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was created
        reading_list = ReadingList.objects.get(name="New Reading List")
        assert reading_list.user == reading_list_user
        assert reading_list.desc == "A new reading list"
        assert not reading_list.is_private


class TestReadingListUpdateView:
    """Tests for the ReadingListUpdateView."""

    def test_reading_list_update_view_requires_login(self, client, public_reading_list):
        """Test that the view requires login."""
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_reading_list_update_view_owner(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that owners can update their lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context
        assert resp.context["title"] == "Edit Reading List"
        assert resp.context["button_text"] == "Update"

    def test_reading_list_update_view_not_owner(
        self, client, other_user, public_reading_list, test_password
    ):
        """Test that non-owners cannot update lists."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_reading_list_update_view_post(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test POST request to update a reading list."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        data = {
            "name": "Updated Reading List",
            "desc": "An updated reading list",
            "is_private": True,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was updated
        public_reading_list.refresh_from_db()
        assert public_reading_list.name == "Updated Reading List"
        assert public_reading_list.desc == "An updated reading list"
        assert public_reading_list.is_private


class TestReadingListDeleteView:
    """Tests for the ReadingListDeleteView."""

    def test_reading_list_delete_view_requires_login(self, client, public_reading_list):
        """Test that the view requires login."""
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_reading_list_delete_view_owner(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that owners can delete their lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

    def test_reading_list_delete_view_not_owner(
        self, client, other_user, public_reading_list, test_password
    ):
        """Test that non-owners cannot delete lists."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_reading_list_delete_view_post(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test POST request to delete a reading list."""
        client.login(username=reading_list_user.username, password=test_password)
        list_id = public_reading_list.id
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was deleted
        assert not ReadingList.objects.filter(id=list_id).exists()


class TestRemoveIssueFromReadingListView:
    """Tests for the RemoveIssueFromReadingListView."""

    def test_remove_issue_view_requires_login(
        self, client, reading_list_with_issues, reading_list_item
    ):
        """Test that the view requires login."""
        url = reverse(
            "reading-list:remove-issue",
            kwargs={
                "slug": reading_list_with_issues.slug,
                "item_pk": reading_list_item.pk,
            },
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_remove_issue_view_owner(
        self, client, reading_list_user, reading_list_with_issues, reading_list_item, test_password
    ):
        """Test that owners can remove issues from their lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse(
            "reading-list:remove-issue",
            kwargs={
                "slug": reading_list_with_issues.slug,
                "item_pk": reading_list_item.pk,
            },
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

    def test_remove_issue_view_not_owner(
        self, client, other_user, reading_list_with_issues, reading_list_item, test_password
    ):
        """Test that non-owners cannot remove issues."""
        client.login(username=other_user.username, password=test_password)
        url = reverse(
            "reading-list:remove-issue",
            kwargs={
                "slug": reading_list_with_issues.slug,
                "item_pk": reading_list_item.pk,
            },
        )
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_remove_issue_view_post(
        self, client, reading_list_user, reading_list_with_issues, reading_list_item, test_password
    ):
        """Test POST request to remove an issue."""
        client.login(username=reading_list_user.username, password=test_password)
        item_id = reading_list_item.id
        url = reverse(
            "reading-list:remove-issue",
            kwargs={
                "slug": reading_list_with_issues.slug,
                "item_pk": reading_list_item.pk,
            },
        )
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the item was removed
        assert not ReadingListItem.objects.filter(id=item_id).exists()
        # Check that the reading list still has 2 issues
        assert reading_list_with_issues.reading_list_items.count() == 2


class TestAddIssueWithAutocompleteView:
    """Tests for the AddIssueWithAutocompleteView."""

    def test_add_issue_view_requires_login(self, client, reading_list_with_issues):
        """Test that the view requires login."""
        url = reverse("reading-list:add-issue", args=[reading_list_with_issues.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_add_issue_view_owner(
        self, client, reading_list_user, reading_list_with_issues, test_password
    ):
        """Test that owners can add issues to their lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[reading_list_with_issues.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context
        assert resp.context["reading_list"] == reading_list_with_issues
        assert len(resp.context["existing_items"]) == 3

    def test_add_issue_view_not_owner(
        self, client, other_user, reading_list_with_issues, test_password
    ):
        """Test that non-owners cannot add issues."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[reading_list_with_issues.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_add_issue_view_post_new_issue(
        self,
        client,
        reading_list_user,
        public_reading_list,
        reading_list_issue_1,
        test_password,
    ):
        """Test POST request to add a new issue."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[public_reading_list.slug])
        data = {
            "issues": [reading_list_issue_1.pk],
            "issue_order": str(reading_list_issue_1.pk),
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the issue was added
        assert public_reading_list.issues.filter(id=reading_list_issue_1.id).exists()

    def test_add_issue_view_post_duplicate(
        self,
        client,
        reading_list_user,
        reading_list_with_issues,
        reading_list_issue_1,
        test_password,
    ):
        """Test POST request to add a duplicate issue."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[reading_list_with_issues.slug])
        # Try to add issue_1 which is already in the list
        data = {
            "issues": [reading_list_issue_1.pk],
            "issue_order": f"{reading_list_issue_1.pk}",
        }
        initial_count = reading_list_with_issues.issues.count()
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Count should not change as it's a duplicate
        assert reading_list_with_issues.issues.count() == initial_count

    def test_add_issue_view_post_reorder(
        self,
        client,
        reading_list_user,
        reading_list_with_issues,
        reading_list_issue_1,
        reading_list_issue_2,
        reading_list_issue_3,
        test_password,
    ):
        """Test POST request to reorder existing issues."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[reading_list_with_issues.slug])
        # Reorder: 3, 1, 2
        data = {
            "issues": [],
            "issue_order": (
                f"{reading_list_issue_3.pk},{reading_list_issue_1.pk},{reading_list_issue_2.pk}"
            ),
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check the new order
        items = reading_list_with_issues.reading_list_items.order_by("order")
        assert items[0].issue == reading_list_issue_3
        assert items[1].issue == reading_list_issue_1
        assert items[2].issue == reading_list_issue_2

    def test_add_issue_view_post_no_changes(
        self, client, reading_list_user, reading_list_with_issues, test_password
    ):
        """Test POST request with no changes."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[reading_list_with_issues.slug])
        data = {
            "issues": [],
            "issue_order": "",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND


class TestAttributionFieldRestrictions:
    """Tests for attribution field restrictions (admin-only)."""

    def test_create_view_non_admin_cannot_see_attribution_fields(
        self, client, reading_list_user, test_password
    ):
        """Test that non-admin users don't see attribution fields in create form."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Attribution fields should not be in the form for non-admin users
        assert "attribution_source" not in form.fields
        assert "attribution_url" not in form.fields
        # Regular fields should still be present
        assert "name" in form.fields
        assert "desc" in form.fields
        assert "is_private" in form.fields

    def test_create_view_admin_can_see_attribution_fields(self, client, admin_user, test_password):
        """Test that admin users see attribution fields in create form."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Admin users should see all fields including attribution fields
        assert "attribution_source" in form.fields
        assert "attribution_url" in form.fields
        assert "name" in form.fields
        assert "desc" in form.fields
        assert "is_private" in form.fields

    def test_create_view_non_admin_cannot_submit_attribution_fields(
        self, client, reading_list_user, test_password
    ):
        """Test that non-admin users cannot submit attribution fields."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:create")
        data = {
            "name": "New Reading List",
            "desc": "A new reading list",
            "is_private": False,
            "attribution_source": ReadingList.AttributionSource.CBRO,
            "attribution_url": "https://example.com/source",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was created WITHOUT attribution data
        reading_list = ReadingList.objects.get(name="New Reading List")
        assert reading_list.user == reading_list_user
        assert reading_list.attribution_source == ""  # Should be empty
        assert reading_list.attribution_url == ""  # Should be empty

    def test_create_view_admin_can_submit_attribution_fields(
        self, client, admin_user, test_password
    ):
        """Test that admin users can submit attribution fields."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:create")
        data = {
            "name": "Admin Reading List",
            "desc": "A reading list with attribution",
            "is_private": False,
            "attribution_source": ReadingList.AttributionSource.CBRO,
            "attribution_url": "https://example.com/source",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was created WITH attribution data
        reading_list = ReadingList.objects.get(name="Admin Reading List")
        assert reading_list.user == admin_user
        assert reading_list.attribution_source == ReadingList.AttributionSource.CBRO
        assert reading_list.attribution_url == "https://example.com/source"

    def test_update_view_non_admin_cannot_see_attribution_fields(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that non-admin users don't see attribution fields in update form."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Attribution fields should not be in the form for non-admin users
        assert "attribution_source" not in form.fields
        assert "attribution_url" not in form.fields
        # Regular fields should still be present
        assert "name" in form.fields
        assert "desc" in form.fields
        assert "is_private" in form.fields

    def test_update_view_admin_can_see_attribution_fields(
        self, client, admin_user, metron_reading_list, test_password
    ):
        """Test that admin users see attribution fields in update form."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:update", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Admin users should see all fields including attribution fields
        assert "attribution_source" in form.fields
        assert "attribution_url" in form.fields
        assert "name" in form.fields
        assert "desc" in form.fields
        assert "is_private" in form.fields

    def test_update_view_non_admin_cannot_modify_attribution_fields(
        self, client, reading_list_user, test_password
    ):
        """Test that non-admin users cannot modify attribution fields."""
        # Create a reading list with attribution
        reading_list = ReadingList.objects.create(
            user=reading_list_user,
            name="List With Attribution",
            desc="Original description",
            is_private=False,
            attribution_source=ReadingList.AttributionSource.CBRO,
            attribution_url="https://example.com/original",
        )

        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[reading_list.slug])
        data = {
            "name": "Updated List",
            "desc": "Updated description",
            "is_private": True,
            "attribution_source": ReadingList.AttributionSource.CMRO,  # Attempt to change
            "attribution_url": "https://example.com/modified",  # Attempt to change
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that regular fields were updated but attribution fields were NOT
        reading_list.refresh_from_db()
        assert reading_list.name == "Updated List"
        assert reading_list.desc == "Updated description"
        assert reading_list.is_private is True
        # Attribution should remain unchanged
        assert reading_list.attribution_source == ReadingList.AttributionSource.CBRO
        assert reading_list.attribution_url == "https://example.com/original"

    def test_update_view_admin_can_modify_attribution_fields(
        self, client, admin_user, metron_reading_list, test_password
    ):
        """Test that admin users can modify attribution fields."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:update", args=[metron_reading_list.slug])
        data = {
            "name": "Updated Metron List",
            "desc": "Updated description",
            "is_private": False,
            "attribution_source": ReadingList.AttributionSource.CMRO,
            "attribution_url": "https://example.com/updated",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all fields including attribution were updated
        metron_reading_list.refresh_from_db()
        assert metron_reading_list.name == "Updated Metron List"
        assert metron_reading_list.desc == "Updated description"
        assert metron_reading_list.attribution_source == ReadingList.AttributionSource.CMRO
        assert metron_reading_list.attribution_url == "https://example.com/updated"


class TestReadingListPagination:
    """Tests for reading list pagination."""

    def test_list_view_pagination_page_1(self, client, reading_list_user):
        """Test that first page of pagination works correctly."""
        # Create 35 reading lists
        for i in range(35):
            ReadingList.objects.create(
                user=reading_list_user,
                name=f"List {i:02d}",  # Zero-padded for consistent ordering
            )
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["reading_lists"]) == 30  # paginate_by = 30
        assert resp.context["page_obj"].number == 1
        assert resp.context["page_obj"].paginator.num_pages == 2

    def test_list_view_pagination_page_2(self, client, reading_list_user):
        """Test that second page of pagination works correctly."""
        # Create 35 reading lists
        for i in range(35):
            ReadingList.objects.create(
                user=reading_list_user,
                name=f"List {i:02d}",
            )
        url = reverse("reading-list:list")
        resp = client.get(url, {"page": 2})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["reading_lists"]) == 5  # Remaining items
        assert resp.context["page_obj"].number == 2

    def test_user_list_view_pagination(self, client, reading_list_user, test_password):
        """Test pagination for user's own reading lists."""
        client.login(username=reading_list_user.username, password=test_password)
        # Create 35 reading lists
        for i in range(35):
            ReadingList.objects.create(
                user=reading_list_user,
                name=f"My List {i:02d}",
            )
        url = reverse("reading-list:my-lists")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["reading_lists"]) == 30
        assert resp.context["page_obj"].number == 1

    def test_search_view_pagination_preserved(self, client, reading_list_user):
        """Test that search results are paginated correctly."""
        # Create 35 reading lists with searchable names
        for i in range(35):
            ReadingList.objects.create(
                user=reading_list_user,
                name=f"Searchable List {i:02d}",
            )
        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "Searchable"})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_paginated"] is True
        assert len(resp.context["reading_lists"]) == 30

        # Test second page
        resp = client.get(url, {"q": "Searchable", "page": 2})
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["reading_lists"]) == 5


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


class TestReadingListDetailViewPagination:
    """Tests for the ReadingListDetailView pagination functionality."""

    def test_reading_list_detail_shows_correct_count(self, client, reading_list_with_many_issues):
        """Test that the detail view shows the correct total count."""
        url = reverse("reading-list:detail", args=[reading_list_with_many_issues.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list_items_count"] == 60

    def test_reading_list_detail_shows_first_50_items(self, client, reading_list_with_many_issues):
        """Test that the detail view only shows the first 50 items."""
        url = reverse("reading-list:detail", args=[reading_list_with_many_issues.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["reading_list_items"]) == 50

    def test_reading_list_detail_items_in_correct_order(
        self, client, reading_list_with_many_issues
    ):
        """Test that items are displayed in the correct order."""
        url = reverse("reading-list:detail", args=[reading_list_with_many_issues.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        items = resp.context["reading_list_items"]
        # Verify items are in order
        for idx, item in enumerate(items, start=1):
            assert item.order == idx

    def test_reading_list_detail_with_few_items_no_pagination(
        self, client, reading_list_with_issues
    ):
        """Test that lists with 50 or fewer items don't paginate."""
        url = reverse("reading-list:detail", args=[reading_list_with_issues.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list_items_count"] == 3
        assert len(resp.context["reading_list_items"]) == 3

    def test_reading_list_detail_empty_list(self, client, public_reading_list):
        """Test that empty lists show count of 0 and no items."""
        url = reverse("reading-list:detail", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list_items_count"] == 0
        assert "reading_list_items" not in resp.context


class TestReadingListItemsLoadMore:
    """Tests for the ReadingListItemsLoadMore HTMX endpoint."""

    def test_load_more_items_success(self, client, reading_list_with_many_issues):
        """Test that the load more endpoint returns additional items."""
        url = reverse("reading-list:items-load-more", args=[reading_list_with_many_issues.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        assert "reading_list_items" in resp.context
        # Should return the remaining 10 items (60 total - 50 offset)
        assert len(resp.context["reading_list_items"]) == 10

    def test_load_more_items_has_more_false(self, client, reading_list_with_many_issues):
        """Test that has_more is False when no more items remain."""
        url = reverse("reading-list:items-load-more", args=[reading_list_with_many_issues.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["has_more"] is False

    @pytest.mark.skip(reason="Parallel test execution causes unique constraint conflicts")
    def test_load_more_items_has_more_true(self, client, reading_list_user, reading_list_series):
        """Test that has_more is True when more items remain."""
        # Create a list with 110 issues
        reading_list = ReadingList.objects.create(
            user=reading_list_user,
            name="Large List",
            is_private=False,
        )

        # Create 110 issues using the existing series

        # Use timestamp to make slugs unique across parallel test runs
        ts = int(time.time() * 1000)
        for i in range(1, 111):
            issue = Issue.objects.create(
                series=reading_list_series,
                number=f"test-{ts}-{i}",  # Unique numbers
                slug=f"large-pagination-test-{ts}-{i}",
                cover_date=date(2020, 1, 1),
                edited_by=reading_list_user,
                created_by=reading_list_user,
            )
            ReadingListItem.objects.create(reading_list=reading_list, issue=issue, order=i)

        url = reverse("reading-list:items-load-more", args=[reading_list.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["has_more"] is True
        assert resp.context["next_offset"] == 100

    def test_load_more_items_correct_offset(self, client, reading_list_with_many_issues):
        """Test that items are returned starting from the correct offset."""
        url = reverse("reading-list:items-load-more", args=[reading_list_with_many_issues.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        items = resp.context["reading_list_items"]
        # First item should have order 51 (offset 50 + 1)
        assert items[0].order == 51

    def test_load_more_items_slug_in_context(self, client, reading_list_with_many_issues):
        """Test that the reading list slug is in the context."""
        url = reverse("reading-list:items-load-more", args=[reading_list_with_many_issues.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list_slug"] == reading_list_with_many_issues.slug

    @pytest.mark.skip(reason="URL resolution behavior is inconsistent across environments")
    def test_load_more_items_not_found(self, client):
        """Test that non-existent reading lists are handled correctly."""
        # Note: Due to URL resolution, this may return various error codes
        # The important thing is that it doesn't succeed
        url = "/reading-lists/non-existent-slug-12345/items-load-more/"
        resp = client.get(url, {"offset": 0}, follow=False)
        # Should not return success - could be 404 or 302 (redirect)
        assert resp.status_code != HTTP_200_OK

    def test_load_more_items_is_owner_true(
        self, client, reading_list_user, reading_list_with_many_issues, test_password
    ):
        """Test that is_owner is True for the reading list owner."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:items-load-more", args=[reading_list_with_many_issues.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_owner"] is True

    def test_load_more_items_is_owner_false(self, client, reading_list_with_many_issues):
        """Test that is_owner is False for non-owners."""
        url = reverse("reading-list:items-load-more", args=[reading_list_with_many_issues.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_owner"] is False

    def test_load_more_items_admin_can_manage_metron(
        self, client, admin_user, metron_reading_list_with_issues, test_password
    ):
        """Test that admins have is_owner True for Metron's lists."""
        # Add more issues to metron's list to test pagination (need 50+ total)

        series = metron_reading_list_with_issues.reading_list_items.first().issue.series
        for i in range(4, 56):
            issue = Issue.objects.create(
                series=series,
                number=str(200 + i),  # Use higher numbers to avoid conflicts
                slug=f"metron-admin-test-issue-{i}",
                cover_date=date(2020, (i % 12) + 1, 1),
                edited_by=admin_user,
                created_by=admin_user,
            )
            ReadingListItem.objects.create(
                reading_list=metron_reading_list_with_issues,
                issue=issue,
                order=i,
            )

        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:items-load-more", args=[metron_reading_list_with_issues.slug])
        resp = client.get(url, {"offset": 50})
        assert resp.status_code == HTTP_200_OK
        assert resp.context["is_owner"] is True

    def test_load_more_respects_private_list_permissions(
        self, client, other_user, private_reading_list, test_password, reading_list_issue_1
    ):
        """Test that non-owners cannot access load more for private lists."""
        # Add an issue to the private list so it's not empty
        ReadingListItem.objects.create(
            reading_list=private_reading_list,
            issue=reading_list_issue_1,
            order=1,
        )

        client.login(username=other_user.username, password=test_password)
        # Use full URL path instead of reverse to avoid potential URL resolution issues
        url = f"/reading-lists/{private_reading_list.slug}/items-load-more/"
        resp = client.get(url, {"offset": 0})
        assert resp.status_code == HTTP_404_NOT_FOUND
