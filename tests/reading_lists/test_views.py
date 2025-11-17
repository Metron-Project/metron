"""Tests for reading_lists views."""

from django.urls import reverse

from reading_lists.models import ReadingList, ReadingListItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404


class TestReadingListListView:
    """Tests for the ReadingListListView."""

    def test_reading_list_list_view_anonymous(
        self, client, public_reading_list, private_reading_list
    ):
        """Test that anonymous users only see public lists."""
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert public_reading_list in resp.context["reading_lists"]
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

    def test_reading_list_list_view_pagination(self, client, reading_list_user):
        """Test that pagination works correctly."""
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

    def test_reading_list_detail_view_public(self, client, public_reading_list):
        """Test viewing a public reading list."""
        url = reverse("reading-list:detail", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"] == public_reading_list
        assert not resp.context["is_owner"]

    def test_reading_list_detail_view_private_anonymous(self, client, private_reading_list):
        """Test that anonymous users cannot view private lists."""
        url = reverse("reading-list:detail", args=[private_reading_list.slug])
        resp = client.get(url)
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

    def test_reading_list_detail_view_with_issues(self, client, reading_list_with_issues):
        """Test viewing a reading list with issues."""
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
