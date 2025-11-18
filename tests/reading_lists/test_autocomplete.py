"""Tests for reading_lists autocomplete functionality."""

from datetime import date

import pytest

from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
from reading_lists.autocomplete import IssueAutocomplete


@pytest.fixture
def autocomplete_publisher(create_user):
    """Create a publisher for autocomplete tests."""
    user = create_user()
    return Publisher.objects.create(
        name="Test Publisher",
        slug="test-publisher",
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def spider_man_series(create_user, autocomplete_publisher, single_issue_type):
    """Create Amazing Spider-Man series."""
    user = create_user()
    return Series.objects.create(
        name="Amazing Spider-Man",
        slug="amazing-spider-man",
        publisher=autocomplete_publisher,
        volume="1",
        year_began=1963,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def batman_series(create_user, autocomplete_publisher, single_issue_type):
    """Create Batman series."""
    user = create_user()
    return Series.objects.create(
        name="Batman",
        slug="batman",
        publisher=autocomplete_publisher,
        volume="1",
        year_began=1940,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def spider_man_issue_1(create_user, spider_man_series):
    """Create Amazing Spider-Man #1."""
    user = create_user()
    return Issue.objects.create(
        series=spider_man_series,
        number="1",
        slug="amazing-spider-man-1",
        cover_date=date(1963, 3, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def spider_man_issue_100(create_user, spider_man_series):
    """Create Amazing Spider-Man #100."""
    user = create_user()
    return Issue.objects.create(
        series=spider_man_series,
        number="100",
        slug="amazing-spider-man-100",
        cover_date=date(1971, 9, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def spider_man_annual_1(create_user, spider_man_series):
    """Create Amazing Spider-Man Annual #1."""
    user = create_user()
    return Issue.objects.create(
        series=spider_man_series,
        number="Annual 1",
        slug="amazing-spider-man-annual-1",
        cover_date=date(1964, 1, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def batman_issue_1(create_user, batman_series):
    """Create Batman #1."""
    user = create_user()
    return Issue.objects.create(
        series=batman_series,
        number="1",
        slug="batman-1",
        cover_date=date(1940, 4, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def batman_issue_100(create_user, batman_series):
    """Create Batman #100."""
    user = create_user()
    return Issue.objects.create(
        series=batman_series,
        number="100",
        slug="batman-100",
        cover_date=date(1956, 6, 1),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def all_test_issues(
    spider_man_issue_1,
    spider_man_issue_100,
    spider_man_annual_1,
    batman_issue_1,
    batman_issue_100,
):
    """Ensure all test issues are created."""
    return [
        spider_man_issue_1,
        spider_man_issue_100,
        spider_man_annual_1,
        batman_issue_1,
        batman_issue_100,
    ]


class TestIssueAutocomplete:
    """Tests for IssueAutocomplete widget."""

    def test_search_without_pound_sign_finds_series_name(self, all_test_issues):
        """Test that searching without # finds issues by series name."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("spider", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find all Spider-Man issues
        assert len(issue_ids) == 3
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[2].id in issue_ids  # Spider-Man Annual #1

    def test_search_without_pound_sign_finds_issue_number(self, all_test_issues):
        """Test that searching without # finds issues by number."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("100", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find both #100 issues
        assert len(issue_ids) == 2
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[4].id in issue_ids  # Batman #100

    def test_search_without_pound_sign_finds_partial_number(self, all_test_issues):
        """Test that searching partial number finds matching issues."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("annual", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find the annual issue
        assert len(issue_ids) == 1
        assert all_test_issues[2].id in issue_ids  # Spider-Man Annual #1

    def test_search_with_series_and_number(self, all_test_issues):
        """Test searching with series name before # and number after #."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("spider#100", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only Spider-Man #100
        assert len(issue_ids) == 1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100

    def test_search_with_full_series_name_and_number(self, all_test_issues):
        """Test searching with full series name and number containing '1'."""
        queryset = IssueAutocomplete.get_query_filtered_queryset(
            "Amazing Spider-Man#1", context=None
        )
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find all Spider-Man issues with "1" in the number (1, 100, Annual 1)
        assert len(issue_ids) == 3
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[2].id in issue_ids  # Spider-Man Annual #1

    def test_search_with_spaces_around_pound(self, all_test_issues):
        """Test searching with spaces around the # character."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("spider # 100", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find Spider-Man #100
        assert len(issue_ids) == 1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100

    def test_search_with_only_pound_and_number(self, all_test_issues):
        """Test searching with just # and number (no series name)."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("#100", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find both #100 issues
        assert len(issue_ids) == 2
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[4].id in issue_ids  # Batman #100

    def test_search_with_series_and_pound_but_no_number(self, all_test_issues):
        """Test searching with series name and # but no number."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("spider#", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should return all issues matching the series name (no number filter applied)
        assert len(issue_ids) == 3
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[2].id in issue_ids  # Spider-Man Annual #1

    def test_search_with_only_pound_sign(self, all_test_issues):
        """Test searching with just # returns empty queryset."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("#", context=None)

        # Should return empty queryset
        assert queryset.count() == 0

    def test_search_with_batman_and_number(self, all_test_issues):
        """Test searching for Batman with number containing '1'."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("batman#1", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find Batman issues with "1" in the number (#1 and #100)
        assert len(issue_ids) == 2
        assert all_test_issues[3].id in issue_ids  # Batman #1
        assert all_test_issues[4].id in issue_ids  # Batman #100

    def test_search_case_insensitive(self, all_test_issues):
        """Test that search is case insensitive."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("SPIDER#100", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find Spider-Man #100 despite uppercase
        assert len(issue_ids) == 1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100

    def test_search_with_partial_series_name_and_number(self, all_test_issues):
        """Test searching with partial series name and number."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("man#100", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find both series with "man" in the name and #100
        assert len(issue_ids) == 2
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[4].id in issue_ids  # Batman #100

    def test_search_with_series_and_partial_number(self, all_test_issues):
        """Test searching with series name and partial number."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("spider#1", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find both Spider-Man #1 and #100 (both contain "1")
        # and Annual 1 (contains "1")
        assert len(issue_ids) == 3
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[2].id in issue_ids  # Spider-Man Annual #1

    def test_search_with_nonexistent_series(self, all_test_issues):
        """Test searching for a series that doesn't exist."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("superman#1", context=None)

        # Should return empty queryset
        assert queryset.count() == 0

    def test_search_with_series_and_nonexistent_number(self, all_test_issues):
        """Test searching for a series with a number that doesn't exist."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("spider#999", context=None)

        # Should return empty queryset
        assert queryset.count() == 0

    def test_get_queryset_includes_series_info(self, spider_man_issue_1):
        """Test that get_queryset includes related series information."""
        queryset = IssueAutocomplete.get_queryset()
        issue = queryset.get(id=spider_man_issue_1.id)

        # Should have series prefetched (no additional queries)
        # Access series.name to verify it's loaded
        assert issue.series.name == "Amazing Spider-Man"
        assert issue.series.series_type is not None

    def test_get_label_for_record(self, spider_man_issue_1):
        """Test that get_label_for_record returns string representation."""
        label = IssueAutocomplete.get_label_for_record(spider_man_issue_1)

        # Should return the string representation of the issue
        assert isinstance(label, str)
        assert label == str(spider_man_issue_1)

    def test_multiple_pound_signs_uses_first(self, all_test_issues):
        """Test that multiple # characters splits on the first one."""
        queryset = IssueAutocomplete.get_query_filtered_queryset("spider#1#extra", context=None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should split on first # and search for "1#extra" in number field
        # This should find issues with "1" in the number
        assert len(issue_ids) == 0  # "1#extra" won't match anything
