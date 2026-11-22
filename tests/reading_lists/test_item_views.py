"""Tests for adding and removing individual reading list issues."""

from django.urls import reverse

from reading_lists.models import ReadingList, ReadingListItem

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403


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

    def test_add_issue_view_malformed_order_is_form_error(
        self, client, reading_list_user, reading_list_with_issues, test_password
    ):
        """A tampered issue_order re-renders the form instead of raising a 500."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[reading_list_with_issues.slug])
        before = list(reading_list_with_issues.reading_list_items.values_list("issue_id", "order"))

        resp = client.post(url, {"issues": [], "issue_order": "1,not-a-number"})
        assert resp.status_code == HTTP_200_OK
        assert "issue_order" in resp.context["form"].errors
        after = list(reading_list_with_issues.reading_list_items.values_list("issue_id", "order"))
        assert after == before

    def test_add_issue_view_adds_and_reorders_together(
        self,
        client,
        reading_list_user,
        public_reading_list,
        reading_list_issue_1,
        reading_list_issue_2,
        reading_list_issue_3,
        test_password,
    ):
        ReadingListItem.objects.create(
            reading_list=public_reading_list, issue=reading_list_issue_1, order=1
        )
        ReadingListItem.objects.create(
            reading_list=public_reading_list, issue=reading_list_issue_2, order=2
        )
        modified_before = ReadingList.objects.get(pk=public_reading_list.pk).modified
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[public_reading_list.slug])
        order = [reading_list_issue_3.pk, reading_list_issue_2.pk, reading_list_issue_1.pk]

        resp = client.post(
            url,
            {
                "issues": [reading_list_issue_3.pk],
                # 999999 is neither on the list nor being added: ignored.
                "issue_order": ",".join(str(pk) for pk in [*order, 999999]),
            },
        )
        assert resp.status_code == HTTP_302_FOUND
        items = list(
            public_reading_list.reading_list_items.order_by("order").values_list(
                "issue_id", "order"
            )
        )
        assert items == [(pk, position) for position, pk in enumerate(order, start=1)]
        assert ReadingList.objects.get(pk=public_reading_list.pk).modified > modified_before

    def test_add_issue_view_reorder_query_count_is_constant(
        self,
        client,
        reading_list_user,
        reading_list_with_many_issues,
        test_password,
        django_assert_max_num_queries,
    ):
        """Reordering doesn't issue a query per entry."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:add-issue", args=[reading_list_with_many_issues.slug])
        reversed_pks = list(
            reading_list_with_many_issues.reading_list_items.order_by("-order").values_list(
                "issue_id", flat=True
            )
        )

        with django_assert_max_num_queries(20):
            resp = client.post(url, {"issues": [], "issue_order": ",".join(map(str, reversed_pks))})
        assert resp.status_code == HTTP_302_FOUND
        assert (
            list(
                reading_list_with_many_issues.reading_list_items.order_by("order").values_list(
                    "issue_id", flat=True
                )
            )
            == reversed_pks
        )

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
