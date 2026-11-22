"""Tests for the reading list detail view and its lazy-loaded items."""

import time
from datetime import date

import pytest
from django.urls import reverse
from django.utils.html import escape

from comicsdb.models.creator import Creator
from comicsdb.models.credits import Credits, Role
from comicsdb.models.issue import Issue
from reading_lists.models import ReadingList, ReadingListItem
from reading_lists.views import build_reading_list_breakdown_context
from users.models import CustomUser

HTTP_200_OK = 200
HTTP_404_NOT_FOUND = 404


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

    def test_reading_list_detail_view_no_previous_next_nav(self, client, public_reading_list):
        """Test that no reading order nav is shown when previous/next are unset."""
        url = reverse("reading-list:detail", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"].previous is None
        assert resp.context["reading_list"].next is None
        assert b"Previous</span>" not in resp.content
        assert b"Next</span>" not in resp.content

    def test_reading_list_detail_view_shows_previous_next_nav(
        self, client, public_reading_list, other_user_reading_list
    ):
        """Test that previous/next links are rendered when set."""
        public_reading_list.next = other_user_reading_list
        public_reading_list.save()

        url = reverse("reading-list:detail", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"].next == other_user_reading_list
        assert escape(other_user_reading_list.name).encode() in resp.content
        assert other_user_reading_list.get_absolute_url().encode() in resp.content

    def test_reading_list_detail_view_shows_synced_previous_nav(
        self, client, public_reading_list, other_user_reading_list
    ):
        """Test that setting A.next = B automatically shows B's previous nav as A."""
        public_reading_list.next = other_user_reading_list
        public_reading_list.save()

        url = reverse("reading-list:detail", args=[other_user_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"].previous == public_reading_list
        assert escape(public_reading_list.name).encode() in resp.content


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


def test_breakdown_featured_creators_use_shared_writer_and_artist_roles(
    reading_list_with_issues, reading_list_issue_1, reading_list_issue_2, create_user
):
    """Plot counts as a writer role and Layouts as an artist role; Colorist isn't featured."""
    user = create_user()
    roles = {
        name: Role.objects.create(name=name, order=order)
        for order, name in enumerate(["Plot", "Layouts", "Colorist"], start=100)
    }
    for name, role, issue in [
        ("Plotter", "Plot", reading_list_issue_1),
        ("Layout Artist", "Layouts", reading_list_issue_2),
        ("Colorist Person", "Colorist", reading_list_issue_1),
    ]:
        creator = Creator.objects.create(
            name=name, slug=name.lower().replace(" ", "-"), edited_by=user, created_by=user
        )
        Credits.objects.create(issue=issue, creator=creator).role.add(roles[role])

    items = list(
        reading_list_with_issues.reading_list_items.select_related("issue__series__publisher")
    )
    featured = build_reading_list_breakdown_context(items)["featured_creators"]

    assert {f["creator"].name: f["roles"] for f in featured} == {
        "Plotter": "Writer",
        "Layout Artist": "Artist",
    }
