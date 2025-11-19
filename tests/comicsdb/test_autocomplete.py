"""Tests for comicsdb autocomplete functionality."""

from datetime import date

import pytest

from comicsdb.autocomplete import (
    ArcAutocomplete,
    CharacterAutocomplete,
    CreatorAutocomplete,
    ImprintAutocomplete,
    IssueAutocomplete,
    PublisherAutocomplete,
    SeriesAutocomplete,
    TeamAutocomplete,
    UniverseAutocomplete,
)
from comicsdb.models.arc import Arc
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.imprint import Imprint
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
from comicsdb.models.team import Team
from comicsdb.models.universe import Universe


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


class TestArcAutocomplete:
    """Tests for ArcAutocomplete widget."""

    def test_search_by_name(self, wwh_arc, fc_arc):
        """Test searching arcs by name."""
        queryset = ArcAutocomplete.get_query_filtered_queryset("world", context=None)
        arc_ids = list(queryset.values_list("id", flat=True))

        assert len(arc_ids) == 1
        assert wwh_arc.id in arc_ids

    def test_search_case_insensitive(self, wwh_arc, fc_arc):
        """Test that search is case insensitive."""
        queryset = ArcAutocomplete.get_query_filtered_queryset("WORLD WAR", context=None)
        arc_ids = list(queryset.values_list("id", flat=True))

        assert len(arc_ids) == 1
        assert wwh_arc.id in arc_ids

    def test_search_partial_match(self, wwh_arc, fc_arc):
        """Test searching with partial name match."""
        queryset = ArcAutocomplete.get_query_filtered_queryset("crisis", context=None)
        arc_ids = list(queryset.values_list("id", flat=True))

        assert len(arc_ids) == 1
        assert fc_arc.id in arc_ids

    def test_search_no_match(self, wwh_arc, fc_arc):
        """Test searching with no matching results."""
        queryset = ArcAutocomplete.get_query_filtered_queryset("infinity", context=None)

        assert queryset.count() == 0

    def test_search_with_accent(self, create_user):
        """Test that unaccent search works for accented characters."""
        user = create_user()
        arc_with_accent = Arc.objects.create(
            name="José's Adventure", slug="joses-adventure", edited_by=user, created_by=user
        )

        # Search without accent should still find it
        queryset = ArcAutocomplete.get_query_filtered_queryset("jose", context=None)
        arc_ids = list(queryset.values_list("id", flat=True))

        assert arc_with_accent.id in arc_ids

    def test_get_label_for_record(self, wwh_arc):
        """Test that get_label_for_record returns string representation."""
        label = ArcAutocomplete.get_label_for_record(wwh_arc)

        assert isinstance(label, str)
        assert label == str(wwh_arc)


class TestCharacterAutocomplete:
    """Tests for CharacterAutocomplete widget."""

    def test_search_by_name(self, superman, batman):
        """Test searching characters by name."""
        queryset = CharacterAutocomplete.get_query_filtered_queryset("super", context=None)
        char_ids = list(queryset.values_list("id", flat=True))

        assert len(char_ids) == 1
        assert superman.id in char_ids

    def test_search_by_alias(self, create_user):
        """Test searching characters by alias field."""
        user = create_user()
        character = Character.objects.create(
            name="Clark Kent",
            slug="clark-kent",
            alias=["Superman", "Man of Steel"],
            edited_by=user,
            created_by=user,
        )

        queryset = CharacterAutocomplete.get_query_filtered_queryset("Man of Steel", context=None)
        char_ids = list(queryset.values_list("id", flat=True))

        assert character.id in char_ids

    def test_search_case_insensitive(self, superman):
        """Test that search is case insensitive."""
        queryset = CharacterAutocomplete.get_query_filtered_queryset("SUPERMAN", context=None)
        char_ids = list(queryset.values_list("id", flat=True))

        assert len(char_ids) == 1
        assert superman.id in char_ids

    def test_search_with_accent_in_name(self, create_user):
        """Test that unaccent search works for accented characters in name."""
        user = create_user()
        character = Character.objects.create(
            name="René Dubois", slug="rene-dubois", edited_by=user, created_by=user
        )

        # Search without accent should still find it
        queryset = CharacterAutocomplete.get_query_filtered_queryset("rene", context=None)
        char_ids = list(queryset.values_list("id", flat=True))

        assert character.id in char_ids

    def test_search_partial_match(self, batman):
        """Test searching with partial name match."""
        queryset = CharacterAutocomplete.get_query_filtered_queryset("bat", context=None)
        char_ids = list(queryset.values_list("id", flat=True))

        assert len(char_ids) == 1
        assert batman.id in char_ids

    def test_search_no_match(self, superman, batman):
        """Test searching with no matching results."""
        queryset = CharacterAutocomplete.get_query_filtered_queryset("wonder", context=None)

        assert queryset.count() == 0

    def test_get_label_for_record(self, superman):
        """Test that get_label_for_record returns string representation."""
        label = CharacterAutocomplete.get_label_for_record(superman)

        assert isinstance(label, str)
        assert label == str(superman)


class TestCreatorAutocomplete:
    """Tests for CreatorAutocomplete widget."""

    def test_search_by_name(self, john_byrne, walter_simonson):
        """Test searching creators by name."""
        queryset = CreatorAutocomplete.get_query_filtered_queryset("byrne", context=None)
        creator_ids = list(queryset.values_list("id", flat=True))

        assert len(creator_ids) == 1
        assert john_byrne.id in creator_ids

    def test_search_by_alias(self, create_user):
        """Test searching creators by alias field."""
        user = create_user()
        creator = Creator.objects.create(
            name="Frank Miller",
            slug="frank-miller",
            alias=["Frank Miller Sr."],
            edited_by=user,
            created_by=user,
        )

        queryset = CreatorAutocomplete.get_query_filtered_queryset("Miller Sr", context=None)
        creator_ids = list(queryset.values_list("id", flat=True))

        assert creator.id in creator_ids

    def test_search_case_insensitive(self, walter_simonson):
        """Test that search is case insensitive."""
        queryset = CreatorAutocomplete.get_query_filtered_queryset("WALTER", context=None)
        creator_ids = list(queryset.values_list("id", flat=True))

        assert len(creator_ids) == 1
        assert walter_simonson.id in creator_ids

    def test_search_with_accent_in_name(self, create_user):
        """Test that unaccent search works for accented characters in name."""
        user = create_user()
        creator = Creator.objects.create(
            name="José García-López", slug="jose-garcia-lopez", edited_by=user, created_by=user
        )

        # Search without accent should still find it
        queryset = CreatorAutocomplete.get_query_filtered_queryset("jose garcia", context=None)
        creator_ids = list(queryset.values_list("id", flat=True))

        assert creator.id in creator_ids

    def test_search_partial_match(self, john_byrne):
        """Test searching with partial name match."""
        queryset = CreatorAutocomplete.get_query_filtered_queryset("john", context=None)
        creator_ids = list(queryset.values_list("id", flat=True))

        assert len(creator_ids) == 1
        assert john_byrne.id in creator_ids

    def test_search_no_match(self, john_byrne, walter_simonson):
        """Test searching with no matching results."""
        queryset = CreatorAutocomplete.get_query_filtered_queryset("stan lee", context=None)

        assert queryset.count() == 0

    def test_get_label_for_record(self, john_byrne):
        """Test that get_label_for_record returns string representation."""
        label = CreatorAutocomplete.get_label_for_record(john_byrne)

        assert isinstance(label, str)
        assert label == str(john_byrne)


class TestPublisherAutocomplete:
    """Tests for PublisherAutocomplete widget."""

    def test_search_by_name(self, dc_comics, marvel):
        """Test searching publishers by name."""
        queryset = PublisherAutocomplete.get_query_filtered_queryset("dc", context=None)
        publisher_ids = list(queryset.values_list("id", flat=True))

        assert len(publisher_ids) == 1
        assert dc_comics.id in publisher_ids

    def test_search_case_insensitive(self, marvel):
        """Test that search is case insensitive."""
        queryset = PublisherAutocomplete.get_query_filtered_queryset("MARVEL", context=None)
        publisher_ids = list(queryset.values_list("id", flat=True))

        assert len(publisher_ids) == 1
        assert marvel.id in publisher_ids

    def test_search_with_accent(self, create_user):
        """Test that unaccent search works for accented characters."""
        user = create_user()
        publisher = Publisher.objects.create(
            name="Éditions Dargaud", slug="editions-dargaud", edited_by=user, created_by=user
        )

        # Search without accent should still find it
        queryset = PublisherAutocomplete.get_query_filtered_queryset("editions", context=None)
        publisher_ids = list(queryset.values_list("id", flat=True))

        assert publisher.id in publisher_ids

    def test_search_partial_match(self, dc_comics):
        """Test searching with partial name match."""
        queryset = PublisherAutocomplete.get_query_filtered_queryset("comics", context=None)
        publisher_ids = list(queryset.values_list("id", flat=True))

        assert len(publisher_ids) == 1
        assert dc_comics.id in publisher_ids

    def test_search_no_match(self, dc_comics, marvel):
        """Test searching with no matching results."""
        queryset = PublisherAutocomplete.get_query_filtered_queryset("image", context=None)

        assert queryset.count() == 0

    def test_get_label_for_record(self, dc_comics):
        """Test that get_label_for_record returns string representation."""
        label = PublisherAutocomplete.get_label_for_record(dc_comics)

        assert isinstance(label, str)
        assert label == str(dc_comics)


class TestSeriesAutocomplete:
    """Tests for SeriesAutocomplete widget."""

    def test_search_by_name(self, fc_series, bat_sups_series):
        """Test searching series by name."""
        queryset = SeriesAutocomplete.get_query_filtered_queryset("final", context=None)
        series_ids = list(queryset.values_list("id", flat=True))

        assert len(series_ids) == 1
        assert fc_series.id in series_ids

    def test_search_case_insensitive(self, bat_sups_series):
        """Test that search is case insensitive."""
        queryset = SeriesAutocomplete.get_query_filtered_queryset("BATMAN", context=None)
        series_ids = list(queryset.values_list("id", flat=True))

        assert len(series_ids) == 1
        assert bat_sups_series.id in series_ids

    def test_search_with_accent(self, create_user, dc_comics, single_issue_type):
        """Test that unaccent search works for accented characters."""
        user = create_user()
        series = Series.objects.create(
            name="Señor Comics",
            slug="senor-comics",
            publisher=dc_comics,
            volume="1",
            year_began=2020,
            series_type=single_issue_type,
            status=Series.Status.ONGOING,
            edited_by=user,
            created_by=user,
        )

        # Search without accent should still find it
        queryset = SeriesAutocomplete.get_query_filtered_queryset("senor", context=None)
        series_ids = list(queryset.values_list("id", flat=True))

        assert series.id in series_ids

    def test_search_partial_match(self, bat_sups_series):
        """Test searching with partial name match."""
        queryset = SeriesAutocomplete.get_query_filtered_queryset("superman", context=None)
        series_ids = list(queryset.values_list("id", flat=True))

        assert len(series_ids) == 1
        assert bat_sups_series.id in series_ids

    def test_search_no_match(self, fc_series, bat_sups_series):
        """Test searching with no matching results."""
        queryset = SeriesAutocomplete.get_query_filtered_queryset("spider-man", context=None)

        assert queryset.count() == 0

    def test_get_queryset_includes_series_type(self, fc_series):
        """Test that get_queryset includes related series_type information."""
        queryset = SeriesAutocomplete.get_queryset()
        series = queryset.get(id=fc_series.id)

        # Should have series_type prefetched (no additional queries)
        assert series.series_type is not None
        assert series.series_type.name is not None

    def test_get_label_for_record(self, fc_series):
        """Test that get_label_for_record returns string representation."""
        label = SeriesAutocomplete.get_label_for_record(fc_series)

        assert isinstance(label, str)
        assert label == str(fc_series)


class TestTeamAutocomplete:
    """Tests for TeamAutocomplete widget."""

    def test_search_by_name(self, teen_titans, avengers):
        """Test searching teams by name."""
        queryset = TeamAutocomplete.get_query_filtered_queryset("teen", context=None)
        team_ids = list(queryset.values_list("id", flat=True))

        assert len(team_ids) == 1
        assert teen_titans.id in team_ids

    def test_search_case_insensitive(self, avengers):
        """Test that search is case insensitive."""
        queryset = TeamAutocomplete.get_query_filtered_queryset("AVENGERS", context=None)
        team_ids = list(queryset.values_list("id", flat=True))

        assert len(team_ids) == 1
        assert avengers.id in team_ids

    def test_search_with_accent(self, create_user):
        """Test that unaccent search works for accented characters."""
        user = create_user()
        team = Team.objects.create(
            name="Los Súper Héroes", slug="los-super-heroes", edited_by=user, created_by=user
        )

        # Search without accent should still find it
        queryset = TeamAutocomplete.get_query_filtered_queryset("super heroes", context=None)
        team_ids = list(queryset.values_list("id", flat=True))

        assert team.id in team_ids

    def test_search_partial_match(self, teen_titans):
        """Test searching with partial name match."""
        queryset = TeamAutocomplete.get_query_filtered_queryset("titans", context=None)
        team_ids = list(queryset.values_list("id", flat=True))

        assert len(team_ids) == 1
        assert teen_titans.id in team_ids

    def test_search_no_match(self, teen_titans, avengers):
        """Test searching with no matching results."""
        queryset = TeamAutocomplete.get_query_filtered_queryset("justice league", context=None)

        assert queryset.count() == 0

    def test_get_label_for_record(self, teen_titans):
        """Test that get_label_for_record returns string representation."""
        label = TeamAutocomplete.get_label_for_record(teen_titans)

        assert isinstance(label, str)
        assert label == str(teen_titans)


class TestUniverseAutocomplete:
    """Tests for UniverseAutocomplete widget."""

    def test_search_by_name(self, earth_2_universe):
        """Test searching universes by name."""
        queryset = UniverseAutocomplete.get_query_filtered_queryset("earth", context=None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert len(universe_ids) == 1
        assert earth_2_universe.id in universe_ids

    def test_search_by_designation(self, earth_2_universe):
        """Test searching universes by designation field."""
        queryset = UniverseAutocomplete.get_query_filtered_queryset("Earth 2", context=None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert len(universe_ids) == 1
        assert earth_2_universe.id in universe_ids

    def test_search_case_insensitive(self, earth_2_universe):
        """Test that search is case insensitive."""
        queryset = UniverseAutocomplete.get_query_filtered_queryset("EARTH", context=None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert len(universe_ids) == 1
        assert earth_2_universe.id in universe_ids

    def test_search_with_accent(self, create_user, dc_comics):
        """Test that unaccent search works for accented characters."""
        user = create_user()
        universe = Universe.objects.create(
            name="Tierra-Ñ",
            slug="tierra-n",
            designation="Tierra-Ñ",
            publisher=dc_comics,
            edited_by=user,
            created_by=user,
        )

        # Search without accent should still find it
        queryset = UniverseAutocomplete.get_query_filtered_queryset("tierra-n", context=None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert universe.id in universe_ids

    def test_search_partial_match(self, earth_2_universe):
        """Test searching with partial name match."""
        queryset = UniverseAutocomplete.get_query_filtered_queryset("2", context=None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert len(universe_ids) == 1
        assert earth_2_universe.id in universe_ids

    def test_search_no_match(self, earth_2_universe):
        """Test searching with no matching results."""
        queryset = UniverseAutocomplete.get_query_filtered_queryset("earth-616", context=None)

        assert queryset.count() == 0

    def test_get_queryset_includes_publisher(self, earth_2_universe):
        """Test that get_queryset includes related publisher information."""
        queryset = UniverseAutocomplete.get_queryset()
        universe = queryset.get(id=earth_2_universe.id)

        # Should have publisher prefetched (no additional queries)
        assert universe.publisher is not None
        assert universe.publisher.name == "DC Comics"

    def test_get_label_for_record(self, earth_2_universe):
        """Test that get_label_for_record returns string representation."""
        label = UniverseAutocomplete.get_label_for_record(earth_2_universe)

        assert isinstance(label, str)
        assert label == str(earth_2_universe)


class TestImprintAutocomplete:
    """Tests for ImprintAutocomplete widget."""

    def test_search_by_name(self, vertigo_imprint, black_label_imprint):
        """Test searching imprints by name."""
        queryset = ImprintAutocomplete.get_query_filtered_queryset("vertigo", context=None)
        imprint_ids = list(queryset.values_list("id", flat=True))

        assert len(imprint_ids) == 1
        assert vertigo_imprint.id in imprint_ids

    def test_search_case_insensitive(self, black_label_imprint):
        """Test that search is case insensitive."""
        queryset = ImprintAutocomplete.get_query_filtered_queryset("BLACK LABEL", context=None)
        imprint_ids = list(queryset.values_list("id", flat=True))

        assert len(imprint_ids) == 1
        assert black_label_imprint.id in imprint_ids

    def test_search_with_accent(self, create_user, dc_comics):
        """Test that unaccent search works for accented characters."""
        user = create_user()
        imprint = Imprint.objects.create(
            name="Años Dorados",
            slug="anos-dorados",
            publisher=dc_comics,
            edited_by=user,
            created_by=user,
        )

        # Search without accent should still find it
        queryset = ImprintAutocomplete.get_query_filtered_queryset("anos", context=None)
        imprint_ids = list(queryset.values_list("id", flat=True))

        assert imprint.id in imprint_ids

    def test_search_partial_match(self, vertigo_imprint):
        """Test searching with partial name match."""
        queryset = ImprintAutocomplete.get_query_filtered_queryset("vert", context=None)
        imprint_ids = list(queryset.values_list("id", flat=True))

        assert len(imprint_ids) == 1
        assert vertigo_imprint.id in imprint_ids

    def test_search_no_match(self, vertigo_imprint, black_label_imprint):
        """Test searching with no matching results."""
        queryset = ImprintAutocomplete.get_query_filtered_queryset("wildstorm", context=None)

        assert queryset.count() == 0

    def test_get_queryset_includes_publisher(self, vertigo_imprint):
        """Test that get_queryset includes related publisher information."""
        queryset = ImprintAutocomplete.get_queryset()
        imprint = queryset.get(id=vertigo_imprint.id)

        # Should have publisher prefetched (no additional queries)
        assert imprint.publisher is not None
        assert imprint.publisher.name == "DC Comics"

    def test_get_label_for_record(self, vertigo_imprint):
        """Test that get_label_for_record returns string representation."""
        label = ImprintAutocomplete.get_label_for_record(vertigo_imprint)

        assert isinstance(label, str)
        assert label == str(vertigo_imprint)
