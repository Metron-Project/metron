"""Tests for user_collection filters."""

from datetime import date

import pytest
from django.urls import reverse

from comicsdb.filters.collection import (
    CollectionSeriesName,
    CollectionViewFilter,
    QuickSearchFilter,
)
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
from user_collection.models import CollectionItem

HTTP_200_OK = 200


@pytest.fixture
def marvel_publisher(create_user):
    """Create Marvel publisher for tests."""
    user = create_user()
    return Publisher.objects.create(name="Marvel", slug="marvel", edited_by=user, created_by=user)


@pytest.fixture
def dc_publisher(create_user):
    """Create DC publisher for tests."""
    user = create_user()
    return Publisher.objects.create(name="DC Comics", slug="dc", edited_by=user, created_by=user)


@pytest.fixture
def spider_series(create_user, marvel_publisher, single_issue_type):
    """Create Amazing Spider-Man series."""
    user = create_user()
    return Series.objects.create(
        name="Amazing Spider-Man",
        slug="amazing-spider-man",
        publisher=marvel_publisher,
        volume="1",
        year_began=1963,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def batman_series(create_user, dc_publisher, single_issue_type):
    """Create Batman series."""
    user = create_user()
    return Series.objects.create(
        name="Batman",
        slug="batman",
        publisher=dc_publisher,
        volume="1",
        year_began=1940,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def spider_issue_1(create_user, spider_series):
    """Create Spider-Man issue #1."""
    user = create_user()
    return Issue.objects.create(
        series=spider_series,
        number="1",
        slug="amazing-spider-man-1",
        cover_date=date(1963, 3, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def spider_issue_100(create_user, spider_series):
    """Create Spider-Man issue #100."""
    user = create_user()
    return Issue.objects.create(
        series=spider_series,
        number="100",
        slug="amazing-spider-man-100",
        cover_date=date(1971, 9, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def batman_issue_1(create_user, batman_series):
    """Create Batman issue #1."""
    user = create_user()
    return Issue.objects.create(
        series=batman_series,
        number="1",
        slug="batman-1",
        cover_date=date(1940, 4, 1),
        edited_by=user,
        created_by=user,
    )


class TestCollectionSeriesNameFilter:
    """Tests for the CollectionSeriesName custom filter."""

    def test_single_word_search(self, collection_user, spider_issue_1, batman_issue_1):
        """Test filtering by single word in series name."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=batman_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filter_instance = CollectionSeriesName()
        result = filter_instance.filter(queryset, "Spider")

        assert result.count() == 1
        assert result.first().issue == spider_issue_1

    def test_multi_word_search(self, collection_user, spider_issue_1, batman_issue_1):
        """Test filtering by multiple words in series name."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=batman_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filter_instance = CollectionSeriesName()
        result = filter_instance.filter(queryset, "Amazing Spider")

        assert result.count() == 1
        assert result.first().issue == spider_issue_1

    def test_case_insensitive_search(self, collection_user, spider_issue_1):
        """Test that search is case-insensitive."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filter_instance = CollectionSeriesName()
        result = filter_instance.filter(queryset, "SPIDER")

        assert result.count() == 1

    def test_empty_value(self, collection_user, spider_issue_1):
        """Test that empty value returns unfiltered queryset."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filter_instance = CollectionSeriesName()
        result = filter_instance.filter(queryset, "")

        assert result.count() == 1


class TestQuickSearchFilter:
    """Tests for the QuickSearchFilter custom filter."""

    def test_search_series_name(self, collection_user, spider_issue_1, batman_issue_1):
        """Test quick search finds series names."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=batman_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filter_instance = QuickSearchFilter()
        result = filter_instance.filter(queryset, "Spider")

        assert result.count() == 1
        assert result.first().issue == spider_issue_1

    def test_search_notes(self, collection_user, spider_issue_1, batman_issue_1):
        """Test quick search finds notes."""
        CollectionItem.objects.create(
            user=collection_user,
            issue=spider_issue_1,
            quantity=1,
            notes="First appearance of Venom",
        )
        CollectionItem.objects.create(
            user=collection_user, issue=batman_issue_1, quantity=1, notes="Classic issue"
        )

        queryset = CollectionItem.objects.filter(user=collection_user)
        filter_instance = QuickSearchFilter()
        result = filter_instance.filter(queryset, "Venom")

        assert result.count() == 1
        assert result.first().issue == spider_issue_1

    def test_search_multiple_fields(self, collection_user, spider_issue_1):
        """Test quick search works across multiple fields."""
        CollectionItem.objects.create(
            user=collection_user, issue=spider_issue_1, quantity=1, notes="Great issue"
        )

        queryset = CollectionItem.objects.filter(user=collection_user)
        filter_instance = QuickSearchFilter()

        # Should find by series name
        result = filter_instance.filter(queryset, "Spider")
        assert result.count() == 1

        # Should find by notes
        result = filter_instance.filter(queryset, "Great")
        assert result.count() == 1

    def test_multi_word_quick_search(self, collection_user, spider_issue_1):
        """Test quick search with multiple words."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filter_instance = QuickSearchFilter()
        result = filter_instance.filter(queryset, "Amazing Spider")

        assert result.count() == 1


class TestCollectionViewFilter:
    """Tests for the CollectionViewFilter FilterSet."""

    def test_filter_by_series_name(self, collection_user, spider_issue_1, batman_issue_1):
        """Test filtering by series name."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=batman_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filterset = CollectionViewFilter({"series_name": "Spider"}, queryset=queryset)

        assert filterset.qs.count() == 1
        assert filterset.qs.first().issue == spider_issue_1

    def test_filter_by_issue_number(self, collection_user, spider_issue_1, spider_issue_100):
        """Test filtering by issue number."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_100, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filterset = CollectionViewFilter({"issue_number": "100"}, queryset=queryset)

        assert filterset.qs.count() == 1
        assert filterset.qs.first().issue == spider_issue_100

    def test_filter_by_publisher_name(self, collection_user, spider_issue_1, batman_issue_1):
        """Test filtering by publisher name."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=batman_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filterset = CollectionViewFilter({"publisher_name": "Marvel"}, queryset=queryset)

        assert filterset.qs.count() == 1
        assert filterset.qs.first().issue == spider_issue_1

    def test_filter_by_book_format(self, collection_user, spider_issue_1, batman_issue_1):
        """Test filtering by book format."""
        CollectionItem.objects.create(
            user=collection_user,
            issue=spider_issue_1,
            quantity=1,
            book_format=CollectionItem.BookFormat.DIGITAL,
        )
        CollectionItem.objects.create(
            user=collection_user,
            issue=batman_issue_1,
            quantity=1,
            book_format=CollectionItem.BookFormat.PRINT,
        )

        queryset = CollectionItem.objects.filter(user=collection_user)
        filterset = CollectionViewFilter({"book_format": "DIGITAL"}, queryset=queryset)

        assert filterset.qs.count() == 1
        assert filterset.qs.first().book_format == CollectionItem.BookFormat.DIGITAL

    def test_filter_by_read_status(self, collection_user, spider_issue_1, batman_issue_1):
        """Test filtering by read status."""
        CollectionItem.objects.create(
            user=collection_user, issue=spider_issue_1, quantity=1, is_read=True
        )
        CollectionItem.objects.create(
            user=collection_user, issue=batman_issue_1, quantity=1, is_read=False
        )

        queryset = CollectionItem.objects.filter(user=collection_user)
        filterset = CollectionViewFilter({"is_read": "true"}, queryset=queryset)

        assert filterset.qs.count() == 1
        assert filterset.qs.first().is_read is True

    def test_combined_filters(
        self, collection_user, spider_issue_1, spider_issue_100, batman_issue_1
    ):
        """Test using multiple filters together."""
        CollectionItem.objects.create(
            user=collection_user,
            issue=spider_issue_1,
            quantity=1,
            book_format=CollectionItem.BookFormat.PRINT,
        )
        CollectionItem.objects.create(
            user=collection_user,
            issue=spider_issue_100,
            quantity=1,
            book_format=CollectionItem.BookFormat.DIGITAL,
        )
        CollectionItem.objects.create(
            user=collection_user,
            issue=batman_issue_1,
            quantity=1,
            book_format=CollectionItem.BookFormat.PRINT,
        )

        queryset = CollectionItem.objects.filter(user=collection_user)
        filterset = CollectionViewFilter(
            {"series_name": "Spider", "book_format": "PRINT"}, queryset=queryset
        )

        assert filterset.qs.count() == 1
        assert filterset.qs.first().issue == spider_issue_1

    def test_quick_search_filter(self, collection_user, spider_issue_1, batman_issue_1):
        """Test the quick search functionality."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=batman_issue_1, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filterset = CollectionViewFilter({"q": "Spider"}, queryset=queryset)

        assert filterset.qs.count() == 1
        assert filterset.qs.first().issue == spider_issue_1

    def test_filter_by_series_type(
        self, collection_user, spider_issue_1, single_issue_type, trade_paperback_type
    ):
        """Test filtering by series type."""
        # Create a TPB series
        user = collection_user
        tpb_series = Series.objects.create(
            name="Spider-Man TPB",
            slug="spider-man-tpb",
            publisher=spider_issue_1.series.publisher,
            volume="1",
            year_began=2000,
            series_type=trade_paperback_type,
            status=Series.Status.COMPLETED,
            edited_by=user,
            created_by=user,
        )
        tpb_issue = Issue.objects.create(
            series=tpb_series,
            number="1",
            slug="spider-man-tpb-1",
            cover_date=date(2000, 1, 1),
            edited_by=user,
            created_by=user,
        )

        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=tpb_issue, quantity=1)

        queryset = CollectionItem.objects.filter(user=collection_user)
        filterset = CollectionViewFilter({"series_type": single_issue_type.id}, queryset=queryset)

        assert filterset.qs.count() == 1
        assert filterset.qs.first().issue.series.series_type == single_issue_type


class TestCollectionListViewFiltering:
    """Tests for the CollectionListView with filtering."""

    def test_list_view_with_series_name_filter(
        self, client, collection_user, spider_issue_1, batman_issue_1, test_password
    ):
        """Test list view filters by series name via URL parameters."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=batman_issue_1, quantity=1)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url, {"series_name": "Spider"})

        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["collection_items"]) == 1
        assert resp.context["collection_items"][0].issue == spider_issue_1

    def test_list_view_with_publisher_filter(
        self, client, collection_user, spider_issue_1, batman_issue_1, test_password
    ):
        """Test list view filters by publisher name."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(user=collection_user, issue=batman_issue_1, quantity=1)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url, {"publisher_name": "Marvel"})

        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["collection_items"]) == 1
        assert resp.context["collection_items"][0].issue.series.publisher.name == "Marvel"

    def test_list_view_with_read_status_filter(
        self, client, collection_user, spider_issue_1, batman_issue_1, test_password
    ):
        """Test list view filters by read status."""
        CollectionItem.objects.create(
            user=collection_user, issue=spider_issue_1, quantity=1, is_read=True
        )
        CollectionItem.objects.create(
            user=collection_user, issue=batman_issue_1, quantity=1, is_read=False
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url, {"is_read": "true"})

        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["collection_items"]) == 1
        assert resp.context["collection_items"][0].is_read is True

    def test_list_view_context_has_filter_options(self, client, collection_user, test_password):
        """Test that list view provides filter options in context."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url)

        assert resp.status_code == HTTP_200_OK
        assert "series_type" in resp.context
        assert "publishers" in resp.context
        assert "book_formats" in resp.context

    def test_list_view_has_active_filters_flag(
        self, client, collection_user, spider_issue_1, test_password
    ):
        """Test that has_active_filters flag is set correctly."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")

        # Without filters
        resp = client.get(url)
        assert resp.context["has_active_filters"] is False

        # With filters
        resp = client.get(url, {"series_name": "Spider"})
        assert resp.context["has_active_filters"] is True

    def test_list_view_pagination_parameter_not_counted_as_filter(
        self, client, collection_user, test_password
    ):
        """Test that pagination 'page' parameter doesn't count as active filter."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url, {"page": "1"})

        assert resp.status_code == HTTP_200_OK
        assert resp.context["has_active_filters"] is False

    def test_list_view_with_quick_search(
        self, client, collection_user, spider_issue_1, batman_issue_1, test_password
    ):
        """Test list view quick search functionality."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)
        CollectionItem.objects.create(
            user=collection_user, issue=batman_issue_1, quantity=1, notes="Dark Knight"
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")

        # Search by series name
        resp = client.get(url, {"q": "Spider"})
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["collection_items"]) == 1

        # Search by notes
        resp = client.get(url, {"q": "Knight"})
        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["collection_items"]) == 1

    def test_list_view_with_multiple_filters(
        self, client, collection_user, spider_issue_1, spider_issue_100, test_password
    ):
        """Test list view with multiple filters applied."""
        CollectionItem.objects.create(
            user=collection_user,
            issue=spider_issue_1,
            quantity=1,
            book_format=CollectionItem.BookFormat.PRINT,
            is_read=True,
        )
        CollectionItem.objects.create(
            user=collection_user,
            issue=spider_issue_100,
            quantity=1,
            book_format=CollectionItem.BookFormat.DIGITAL,
            is_read=False,
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url, {"series_name": "Spider", "book_format": "PRINT", "is_read": "true"})

        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["collection_items"]) == 1
        assert resp.context["collection_items"][0].issue == spider_issue_1

    def test_list_view_no_results_with_filters(
        self, client, collection_user, spider_issue_1, test_password
    ):
        """Test list view shows no results when filters don't match."""
        CollectionItem.objects.create(user=collection_user, issue=spider_issue_1, quantity=1)

        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:list")
        resp = client.get(url, {"series_name": "NonExistent"})

        assert resp.status_code == HTTP_200_OK
        assert len(resp.context["collection_items"]) == 0
        assert resp.context["has_active_filters"] is True
