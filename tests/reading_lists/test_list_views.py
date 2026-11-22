"""Tests for the reading list list, search and per-user list views."""

from django.urls import reverse

from reading_lists.models import ReadingList, ReadingListRating
from users.models import CustomUser

HTTP_200_OK = 200
HTTP_302_FOUND = 302


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

    def test_filter_by_publisher(
        self, client, public_reading_list, reading_list_with_issues, reading_list_publisher
    ):
        """Test filtering reading lists by publisher name."""
        url = reverse("reading-list:list")
        resp = client.get(url, {"publisher": reading_list_publisher.name})
        assert resp.status_code == HTTP_200_OK
        assert reading_list_with_issues in resp.context["reading_lists"]
        # List with no issues has no publisher association
        assert public_reading_list not in resp.context["reading_lists"]

    def test_filter_by_publisher_no_results(self, client, reading_list_with_issues):
        """Test that filtering by a non-existent publisher returns no results."""
        url = reverse("reading-list:list")
        resp = client.get(url, {"publisher": "Nonexistent Publisher"})
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["reading_lists"]) == 0

    def test_filter_by_publisher_no_duplicates(self, client, reading_list_with_issues):
        """Test that filtering by publisher does not return duplicate reading lists."""
        url = reverse("reading-list:list")
        resp = client.get(url, {"publisher": "Test Publisher"})
        assert resp.status_code == HTTP_200_OK
        reading_lists = list(resp.context["reading_lists"])
        assert len(reading_lists) == len({rl.pk for rl in reading_lists})

    def test_filter_by_list_type(self, client, reading_list_user, public_reading_list):
        """Test filtering reading lists by list_type."""
        story_list = ReadingList.objects.create(
            user=reading_list_user,
            name="Story List",
            list_type=ReadingList.ListType.STORY,
        )
        url = reverse("reading-list:list")
        resp = client.get(url, {"list_type": ReadingList.ListType.STORY})
        assert resp.status_code == HTTP_200_OK
        assert story_list in resp.context["reading_lists"]
        assert public_reading_list not in resp.context["reading_lists"]

    def test_list_type_choices_in_context(self, client, db):
        """Test that list_type choices are passed to the template context."""
        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "list_types" in resp.context
        assert list(resp.context["list_types"]) == list(ReadingList.ListType.choices)

    def test_issue_count_not_inflated_by_ratings(
        self, client, create_user, reading_list_with_issues
    ):
        """Regression test: issue_count must not be multiplied by the number of ratings.

        When annotating with both Count("issues") and Count/Avg on "ratings", Django
        performs a cross-join that inflates counts unless distinct=True is used.
        A list with 3 issues and 2 ratings should report issue_count=3, not 6.
        """
        rater1 = create_user()
        rater2 = create_user()
        ReadingListRating.objects.create(
            reading_list=reading_list_with_issues, user=rater1, rating=4
        )
        ReadingListRating.objects.create(
            reading_list=reading_list_with_issues, user=rater2, rating=5
        )

        url = reverse("reading-list:list")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        rl = next(r for r in resp.context["reading_lists"] if r.pk == reading_list_with_issues.pk)
        assert rl.issue_count == 3


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

    def test_issue_count_not_inflated_by_ratings(
        self, client, create_user, reading_list_with_issues
    ):
        """Regression test: issue_count must not be multiplied by the number of ratings."""
        rater1 = create_user()
        rater2 = create_user()
        ReadingListRating.objects.create(
            reading_list=reading_list_with_issues, user=rater1, rating=4
        )
        ReadingListRating.objects.create(
            reading_list=reading_list_with_issues, user=rater2, rating=5
        )

        url = reverse("reading-list:search")
        resp = client.get(url, {"q": "List With Issues"})
        assert resp.status_code == HTTP_200_OK
        rl = next(r for r in resp.context["reading_lists"] if r.pk == reading_list_with_issues.pk)
        assert rl.issue_count == 3

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

    def test_issue_count_not_inflated_by_ratings(
        self,
        client,
        create_user,
        reading_list_user,
        reading_list_with_issues,
        test_password,
    ):
        """Regression test: issue_count must not be multiplied by the number of ratings."""
        rater1 = create_user()
        rater2 = create_user()
        ReadingListRating.objects.create(
            reading_list=reading_list_with_issues, user=rater1, rating=4
        )
        ReadingListRating.objects.create(
            reading_list=reading_list_with_issues, user=rater2, rating=5
        )

        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:my-lists")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        rl = next(r for r in resp.context["reading_lists"] if r.pk == reading_list_with_issues.pk)
        assert rl.issue_count == 3


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
