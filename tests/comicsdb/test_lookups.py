"""Tests for comicsdb lookup functionality."""

from datetime import date

import pytest
from django.urls import reverse
from django.utils.text import slugify
from izaya.lookups import registry

from comicsdb.lookups import (
    ArcLookup,
    CharacterLookup,
    CreatorLookup,
    ImprintLookup,
    IssueLookup,
    PublisherLookup,
    SeriesLookup,
    TeamLookup,
    UniverseLookup,
    unaccent,
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

HTTP_200_OK = 200
HTTP_403_FORBIDDEN = 403


@pytest.fixture
def lookup_publisher(create_user):
    """Create a publisher for lookup tests."""
    user = create_user()
    return Publisher.objects.create(
        name="Test Publisher",
        slug="test-publisher",
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def spider_man_series(create_user, lookup_publisher, single_issue_type):
    """Create Amazing Spider-Man series."""
    user = create_user()
    return Series.objects.create(
        name="Amazing Spider-Man",
        slug="amazing-spider-man",
        publisher=lookup_publisher,
        volume="1",
        year_began=1963,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def batman_series(create_user, lookup_publisher, single_issue_type):
    """Create Batman series."""
    user = create_user()
    return Series.objects.create(
        name="Batman",
        slug="batman",
        publisher=lookup_publisher,
        volume="1",
        year_began=1940,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def spider_man_2022_series(create_user, lookup_publisher, single_issue_type):
    """Create Amazing Spider-Man (2022) series."""
    user = create_user()
    return Series.objects.create(
        name="Amazing Spider-Man",
        slug="amazing-spider-man-2022",
        publisher=lookup_publisher,
        volume="6",
        year_began=2022,
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
def spider_man_2022_issue_1(create_user, spider_man_2022_series):
    """Create Amazing Spider-Man (2022) #1."""
    user = create_user()
    return Issue.objects.create(
        series=spider_man_2022_series,
        number="1",
        slug="amazing-spider-man-2022-1",
        cover_date=date(2022, 4, 1),
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


class TestIssueLookup:
    """Tests for IssueLookup widget."""

    def test_search_without_pound_sign_finds_series_name(self, all_test_issues):
        """Test that searching without # finds issues by series name."""
        queryset = IssueLookup().search("spider", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find all Spider-Man issues
        assert len(issue_ids) == 3
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[2].id in issue_ids  # Spider-Man Annual #1

    def test_search_without_pound_sign_finds_issue_number(self, all_test_issues):
        """Test that searching without # finds issues by number."""
        queryset = IssueLookup().search("100", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find both #100 issues
        assert len(issue_ids) == 2
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[4].id in issue_ids  # Batman #100

    def test_search_without_pound_sign_finds_partial_number(self, all_test_issues):
        """Test that searching partial number finds matching issues."""
        queryset = IssueLookup().search("annual", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find the annual issue
        assert len(issue_ids) == 1
        assert all_test_issues[2].id in issue_ids  # Spider-Man Annual #1

    def test_search_with_series_and_number(self, all_test_issues):
        """Test searching with series name before # and number after #."""
        queryset = IssueLookup().search("spider#100", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only Spider-Man #100
        assert len(issue_ids) == 1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100

    def test_search_with_full_series_name_and_number(self, all_test_issues):
        """Test searching with full series name and exact number match."""
        queryset = IssueLookup().search("Amazing Spider-Man#1", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only Spider-Man #1 (exact number match)
        assert len(issue_ids) == 1
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1

    def test_search_with_spaces_around_pound(self, all_test_issues):
        """Test searching with spaces around the # character."""
        queryset = IssueLookup().search("spider # 100", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find Spider-Man #100
        assert len(issue_ids) == 1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100

    def test_search_with_only_pound_and_number(self, all_test_issues):
        """Test searching with just # and number (no series name)."""
        queryset = IssueLookup().search("#100", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find both #100 issues
        assert len(issue_ids) == 2
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[4].id in issue_ids  # Batman #100

    def test_search_with_series_and_pound_but_no_number(self, all_test_issues):
        """Test searching with series name and # but no number."""
        queryset = IssueLookup().search("spider#", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should return all issues matching the series name (no number filter applied)
        assert len(issue_ids) == 3
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[2].id in issue_ids  # Spider-Man Annual #1

    def test_search_with_only_pound_sign(self, all_test_issues):
        """Test searching with just # returns empty queryset."""
        queryset = IssueLookup().search("#", None)

        # Should return empty queryset
        assert queryset.count() == 0

    def test_search_with_batman_and_number(self, all_test_issues):
        """Test searching for Batman with exact number match."""
        queryset = IssueLookup().search("batman#1", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only Batman #1 (exact number match)
        assert len(issue_ids) == 1
        assert all_test_issues[3].id in issue_ids  # Batman #1

    def test_search_case_insensitive(self, all_test_issues):
        """Test that search is case insensitive."""
        queryset = IssueLookup().search("SPIDER#100", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find Spider-Man #100 despite uppercase
        assert len(issue_ids) == 1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100

    def test_search_with_partial_series_name_and_number(self, all_test_issues):
        """Test searching with partial series name and number."""
        queryset = IssueLookup().search("man#100", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find both series with "man" in the name and #100
        assert len(issue_ids) == 2
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100
        assert all_test_issues[4].id in issue_ids  # Batman #100

    def test_search_with_series_and_exact_number(self, all_test_issues):
        """Test searching with series name and exact number match."""
        queryset = IssueLookup().search("spider#1", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only Spider-Man #1 (exact number match)
        assert len(issue_ids) == 1
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1

    def test_search_with_nonexistent_series(self, all_test_issues):
        """Test searching for a series that doesn't exist."""
        queryset = IssueLookup().search("superman#1", None)

        # Should return empty queryset
        assert queryset.count() == 0

    def test_search_with_series_and_nonexistent_number(self, all_test_issues):
        """Test searching for a series with a number that doesn't exist."""
        queryset = IssueLookup().search("spider#999", None)

        # Should return empty queryset
        assert queryset.count() == 0

    def test_search_without_pound_sign_and_accented_series(self, all_test_issues):
        """Test that accents are ignored when searching series names without '#'."""
        queryset = IssueLookup().search("Spíder", None)

        assert set(queryset) == set(all_test_issues[:3])

    def test_search_with_pound_sign_and_accented_series(self, all_test_issues):
        """Test that accents in the series part of a '#' search are ignored."""
        queryset = IssueLookup().search("Spíder#1", None)

        assert list(queryset) == [all_test_issues[0]]

    def test_get_queryset_includes_series_info(self, spider_man_issue_1):
        """Test that get_queryset includes related series information."""
        queryset = IssueLookup().get_base_queryset()
        issue = queryset.get(id=spider_man_issue_1.id)

        # Should have series prefetched (no additional queries)
        # Access series.name to verify it's loaded
        assert issue.series.name == "Amazing Spider-Man"
        assert issue.series.series_type is not None

    def test_get_label_for_record(self, spider_man_issue_1):
        """Test that get_label_for_record returns string representation."""
        label = IssueLookup().label(spider_man_issue_1)

        # Should return the string representation of the issue
        assert isinstance(label, str)
        assert label == str(spider_man_issue_1)

    def test_multiple_pound_signs_uses_first(self, all_test_issues):
        """Test that multiple # characters splits on the first one."""
        queryset = IssueLookup().search("spider#1#extra", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should split on first # and search for "1#extra" in number field
        # This should find issues with "1" in the number
        assert len(issue_ids) == 0  # "1#extra" won't match anything

    def test_search_with_words_in_different_order(self, all_test_issues):
        """Test that word order in series name doesn't matter."""
        queryset = IssueLookup().search("Spider Amazing#1", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find Spider-Man #1 with reversed word order (exact number match)
        assert len(issue_ids) == 1
        assert all_test_issues[0].id in issue_ids  # Spider-Man #1

    def test_search_with_words_in_different_order_exact_number(self, all_test_issues):
        """Test word order independence with exact number match."""
        queryset = IssueLookup().search("Spider Amazing#100", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only Spider-Man #100
        assert len(issue_ids) == 1
        assert all_test_issues[1].id in issue_ids  # Spider-Man #100

    def test_search_with_year_filter(self, spider_man_issue_1, spider_man_2022_issue_1):
        """Test that year in parentheses filters by series year_began."""
        queryset = IssueLookup().search("Amazing Spider-Man (2022)#1", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only the 2022 series issue
        assert len(issue_ids) == 1
        assert spider_man_2022_issue_1.id in issue_ids
        assert spider_man_issue_1.id not in issue_ids

    def test_search_with_year_filter_1963(self, spider_man_issue_1, spider_man_2022_issue_1):
        """Test year filter for 1963 series."""
        queryset = IssueLookup().search("Amazing Spider-Man (1963)#1", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only the 1963 series issue
        assert len(issue_ids) == 1
        assert spider_man_issue_1.id in issue_ids
        assert spider_man_2022_issue_1.id not in issue_ids

    def test_search_with_year_and_word_order_independence(
        self, spider_man_issue_1, spider_man_2022_issue_1
    ):
        """Test that year filter works with word order independence."""
        # spider_man_issue_1 needed to ensure both series exist in DB
        queryset = IssueLookup().search("Spider Amazing (2022)#1", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find only the 2022 series issue with reversed word order
        assert len(issue_ids) == 1
        assert spider_man_2022_issue_1.id in issue_ids
        assert spider_man_issue_1.id not in issue_ids

    def test_search_with_year_only(self, spider_man_issue_1, spider_man_2022_issue_1):
        """Test searching with just year (no series name)."""
        # spider_man_issue_1 needed to ensure both series exist in DB
        queryset = IssueLookup().search("(2022)#1", None)
        issue_ids = list(queryset.values_list("id", flat=True))

        # Should find the 2022 series issue (year filter only, no name filter)
        assert len(issue_ids) == 1
        assert spider_man_2022_issue_1.id in issue_ids
        assert spider_man_issue_1.id not in issue_ids

    def test_search_with_nonexistent_year(self, spider_man_issue_1, spider_man_2022_issue_1):
        """Test searching with a year that doesn't match any series."""
        # Both fixtures needed to ensure issues exist but none match year 2000
        assert spider_man_issue_1 is not None
        assert spider_man_2022_issue_1 is not None
        queryset = IssueLookup().search("Amazing Spider-Man (2000)#1", None)

        # Should return empty queryset
        assert queryset.count() == 0


class TestArcLookup:
    """Tests for ArcLookup widget."""

    def test_search_by_name(self, wwh_arc, fc_arc):
        """Test searching arcs by name."""
        queryset = ArcLookup().search("world", None)
        arc_ids = list(queryset.values_list("id", flat=True))

        assert len(arc_ids) == 1
        assert wwh_arc.id in arc_ids

    def test_search_case_insensitive(self, wwh_arc, fc_arc):
        """Test that search is case insensitive."""
        queryset = ArcLookup().search("WORLD WAR", None)
        arc_ids = list(queryset.values_list("id", flat=True))

        assert len(arc_ids) == 1
        assert wwh_arc.id in arc_ids

    def test_search_partial_match(self, wwh_arc, fc_arc):
        """Test searching with partial name match."""
        queryset = ArcLookup().search("crisis", None)
        arc_ids = list(queryset.values_list("id", flat=True))

        assert len(arc_ids) == 1
        assert fc_arc.id in arc_ids

    def test_search_no_match(self, wwh_arc, fc_arc):
        """Test searching with no matching results."""
        queryset = ArcLookup().search("infinity", None)

        assert queryset.count() == 0

    def test_search_with_accent(self, create_user):
        """Test that unaccent search works for accented characters."""
        user = create_user()
        arc_with_accent = Arc.objects.create(
            name="José's Adventure", slug="joses-adventure", edited_by=user, created_by=user
        )

        # Search without accent should still find it
        queryset = ArcLookup().search("jose", None)
        arc_ids = list(queryset.values_list("id", flat=True))

        assert arc_with_accent.id in arc_ids

    def test_get_label_for_record(self, wwh_arc):
        """Test that get_label_for_record returns string representation."""
        label = ArcLookup().label(wwh_arc)

        assert isinstance(label, str)
        assert label == str(wwh_arc)


class TestCharacterLookup:
    """Tests for CharacterLookup widget."""

    def test_search_by_name(self, superman, batman):
        """Test searching characters by name."""
        queryset = CharacterLookup().search("super", None)
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

        queryset = CharacterLookup().search("Man of Steel", None)
        char_ids = list(queryset.values_list("id", flat=True))

        assert character.id in char_ids

    def test_search_case_insensitive(self, superman):
        """Test that search is case insensitive."""
        queryset = CharacterLookup().search("SUPERMAN", None)
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
        queryset = CharacterLookup().search("rene", None)
        char_ids = list(queryset.values_list("id", flat=True))

        assert character.id in char_ids

    def test_search_partial_match(self, batman):
        """Test searching with partial name match."""
        queryset = CharacterLookup().search("bat", None)
        char_ids = list(queryset.values_list("id", flat=True))

        assert len(char_ids) == 1
        assert batman.id in char_ids

    def test_search_no_match(self, superman, batman):
        """Test searching with no matching results."""
        queryset = CharacterLookup().search("wonder", None)

        assert queryset.count() == 0

    def test_get_label_for_record(self, superman):
        """Test that get_label_for_record returns string representation."""
        label = CharacterLookup().label(superman)

        assert isinstance(label, str)
        assert label == str(superman)


class TestCreatorLookup:
    """Tests for CreatorLookup widget."""

    def test_search_by_name(self, john_byrne, walter_simonson):
        """Test searching creators by name."""
        queryset = CreatorLookup().search("byrne", None)
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

        queryset = CreatorLookup().search("Miller Sr", None)
        creator_ids = list(queryset.values_list("id", flat=True))

        assert creator.id in creator_ids

    def test_search_case_insensitive(self, walter_simonson):
        """Test that search is case insensitive."""
        queryset = CreatorLookup().search("WALTER", None)
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
        queryset = CreatorLookup().search("jose garcia", None)
        creator_ids = list(queryset.values_list("id", flat=True))

        assert creator.id in creator_ids

    def test_search_with_accented_query(self, create_user):
        """Test that an accented query matches, since the query is unaccented as well."""
        user = create_user()
        creator = Creator.objects.create(
            name="Ana Peña", slug="ana-pena", edited_by=user, created_by=user
        )

        assert creator in CreatorLookup().search("Peña", None)

    def test_leading_space_with_accented_query(self, create_user):
        """Test that an accented surname search matches and gets surname priority."""
        user = create_user()
        for name in ("Peña Ruiz", "Luis Peñaloza", "Ana Peña"):
            Creator.objects.create(name=name, slug=slugify(name), edited_by=user, created_by=user)

        names = list(CreatorLookup().search(" Peña", None).values_list("name", flat=True))

        assert names == ["Ana Peña", "Luis Peñaloza"]

    def test_accented_query_matches_accented_alias(self, create_user):
        """Test that aliases, which aren't unaccented, still get the query as typed."""
        user = create_user()
        creator = Creator.objects.create(
            name="John Smith",
            slug="john-smith",
            alias=["Señor Smith"],
            edited_by=user,
            created_by=user,
        )

        assert creator in CreatorLookup().search("Señor", None)

    def test_search_partial_match(self, john_byrne):
        """Test searching with partial name match."""
        queryset = CreatorLookup().search("john", None)
        creator_ids = list(queryset.values_list("id", flat=True))

        assert len(creator_ids) == 1
        assert john_byrne.id in creator_ids

    def test_search_no_match(self, john_byrne, walter_simonson):
        """Test searching with no matching results."""
        queryset = CreatorLookup().search("stan lee", None)

        assert queryset.count() == 0

    @pytest.fixture
    def camerons(self, create_user):
        """Create creators with "Cameron" as a first, middle and last name."""
        user = create_user()
        return {
            name: Creator.objects.create(
                name=name, slug=slugify(name), edited_by=user, created_by=user
            )
            for name in ("Cameron Stewart", "Don Cameron", "Jo Cameron Smith", "Ann Camerons")
        }

    def test_leading_space_is_kept(self):
        """Test that one leading space survives cleaning, so it can mean a surname search."""
        assert CreatorLookup().clean_query("   Cameron  ") == " Cameron"

    def test_surrounding_whitespace_is_stripped_without_a_leading_space(self):
        """Test that a query without a leading space is stripped as usual."""
        assert CreatorLookup().clean_query("Cameron  ") == "Cameron"

    def test_leading_space_skips_first_names(self, camerons):
        """Test that a leading space only matches names after the first."""
        names = list(CreatorLookup().search(" cameron", None).values_list("name", flat=True))

        assert "Cameron Stewart" not in names
        assert set(names) == {"Don Cameron", "Jo Cameron Smith", "Ann Camerons"}

    def test_leading_space_puts_names_ending_with_the_query_first(self, camerons):
        """Test that surname matches come before middle names and partial words."""
        names = list(CreatorLookup().search(" cameron", None).values_list("name", flat=True))

        assert names[0] == "Don Cameron"

    def test_short_leading_space_query_drops_the_space(self):
        """Test that the leading space doesn't count toward the minimum length."""
        assert CreatorLookup().clean_query(" Ca") == "Ca"

    def test_leading_non_space_whitespace_is_stripped(self):
        """Test that a leading tab or NBSP doesn't trigger a surname search."""
        assert CreatorLookup().clean_query("\tCameron") == "Cameron"
        assert CreatorLookup().clean_query("\u00a0Cameron") == "Cameron"

    def test_several_leading_spaces_search_by_surname(self, camerons):
        """Test that search() treats several leading spaces like one."""
        names = list(CreatorLookup().search("   cameron", None).values_list("name", flat=True))

        assert set(names) == {"Don Cameron", "Jo Cameron Smith", "Ann Camerons"}

    def test_leading_space_alias_match_does_not_outrank_surnames(self, camerons):
        """Test that a first-name match found through an alias sorts after surname matches."""
        creator = camerons["Cameron Stewart"]
        creator.alias = ["John Cameron Jr."]
        creator.save()

        names = list(CreatorLookup().search(" cameron", None).values_list("name", flat=True))

        assert names[0] == "Don Cameron"
        assert names.index("Cameron Stewart") > names.index("Don Cameron")

    def test_short_leading_space_query_shows_min_length_message(self, client, create_user):
        """Test that the endpoint asks for more text when only two characters follow the space."""
        client.force_login(create_user())
        resp = client.get(reverse("izaya:search", args=["CreatorLookup"]), {"q": " Ca"})

        assert resp.status_code == HTTP_200_OK
        assert str(CreatorLookup.min_length) in resp.content.decode()

    def test_leading_space_matches_aliases(self, create_user):
        """Test that a leading space also searches later names in aliases."""
        user = create_user()
        creator = Creator.objects.create(
            name="Frank Miller",
            slug="frank-miller",
            alias=["Frank Miller Sr."],
            edited_by=user,
            created_by=user,
        )

        assert creator in CreatorLookup().search(" sr.", None)

    def test_without_leading_space_first_names_match(self, camerons):
        """Test that a plain query still matches first names, ranked first."""
        names = list(CreatorLookup().search("cameron", None).values_list("name", flat=True))

        assert names[0] == "Cameron Stewart"
        assert len(names) == len(camerons)

    def test_search_endpoint_keeps_leading_space(self, client, create_user, camerons):
        """Test that the search endpoint passes the leading space through to the lookup."""
        client.force_login(create_user())
        resp = client.get(reverse("izaya:search", args=["CreatorLookup"]), {"q": " Cameron"})

        assert resp.status_code == HTTP_200_OK
        assert b"Don Cameron" in resp.content
        assert b"Cameron Stewart" not in resp.content

    def test_get_label_for_record(self, john_byrne):
        """Test that get_label_for_record returns string representation."""
        label = CreatorLookup().label(john_byrne)

        assert isinstance(label, str)
        assert label == str(john_byrne)


class TestPublisherLookup:
    """Tests for PublisherLookup widget."""

    def test_search_by_name(self, dc_comics, marvel):
        """Test searching publishers by name."""
        queryset = PublisherLookup().search("dc", None)
        publisher_ids = list(queryset.values_list("id", flat=True))

        assert len(publisher_ids) == 1
        assert dc_comics.id in publisher_ids

    def test_search_case_insensitive(self, marvel):
        """Test that search is case insensitive."""
        queryset = PublisherLookup().search("MARVEL", None)
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
        queryset = PublisherLookup().search("editions", None)
        publisher_ids = list(queryset.values_list("id", flat=True))

        assert publisher.id in publisher_ids

    def test_search_partial_match(self, dc_comics):
        """Test searching with partial name match."""
        queryset = PublisherLookup().search("comics", None)
        publisher_ids = list(queryset.values_list("id", flat=True))

        assert len(publisher_ids) == 1
        assert dc_comics.id in publisher_ids

    def test_search_no_match(self, dc_comics, marvel):
        """Test searching with no matching results."""
        queryset = PublisherLookup().search("image", None)

        assert queryset.count() == 0

    def test_get_label_for_record(self, dc_comics):
        """Test that get_label_for_record returns string representation."""
        label = PublisherLookup().label(dc_comics)

        assert isinstance(label, str)
        assert label == str(dc_comics)


class TestSeriesLookup:
    """Tests for SeriesLookup widget."""

    def test_search_by_name(self, fc_series, bat_sups_series):
        """Test searching series by name."""
        queryset = SeriesLookup().search("final", None)
        series_ids = list(queryset.values_list("id", flat=True))

        assert len(series_ids) == 1
        assert fc_series.id in series_ids

    def test_search_case_insensitive(self, bat_sups_series):
        """Test that search is case insensitive."""
        queryset = SeriesLookup().search("BATMAN", None)
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
        queryset = SeriesLookup().search("senor", None)
        series_ids = list(queryset.values_list("id", flat=True))

        assert series.id in series_ids

    def test_search_partial_match(self, bat_sups_series):
        """Test searching with partial name match."""
        queryset = SeriesLookup().search("superman", None)
        series_ids = list(queryset.values_list("id", flat=True))

        assert len(series_ids) == 1
        assert bat_sups_series.id in series_ids

    def test_search_by_alt_names(self, create_user, dc_comics, single_issue_type):
        """Test searching series by alt_names field."""
        user = create_user()
        series = Series.objects.create(
            name="Betty and Veronica Spectacular",
            slug="betty-and-veronica-spectacular",
            publisher=dc_comics,
            volume="1",
            year_began=1992,
            series_type=single_issue_type,
            status=Series.Status.CANCELLED,
            alt_names=["Betty & Veronica Spectacular"],
            edited_by=user,
            created_by=user,
        )

        queryset = SeriesLookup().search("Betty & Veronica Spectacular", None)
        series_ids = list(queryset.values_list("id", flat=True))

        assert series.id in series_ids

    def test_search_no_match(self, fc_series, bat_sups_series):
        """Test searching with no matching results."""
        queryset = SeriesLookup().search("spider-man", None)

        assert queryset.count() == 0

    def test_get_queryset_includes_publisher(self, fc_series):
        """Test that get_queryset includes related publisher information."""
        queryset = SeriesLookup().get_base_queryset()
        series = queryset.get(id=fc_series.id)

        # Should have publisher prefetched (no additional queries)
        assert series.publisher is not None
        assert series.publisher.name == "DC Comics"

    def test_get_label_for_record(self, fc_series):
        """Test that get_label_for_record includes the volume and publisher name."""
        label = SeriesLookup().label(fc_series)

        assert isinstance(label, str)
        assert label == f"{fc_series} · v{fc_series.volume} · {fc_series.publisher.name}"


class TestTeamLookup:
    """Tests for TeamLookup widget."""

    def test_search_by_name(self, teen_titans, avengers):
        """Test searching teams by name."""
        queryset = TeamLookup().search("teen", None)
        team_ids = list(queryset.values_list("id", flat=True))

        assert len(team_ids) == 1
        assert teen_titans.id in team_ids

    def test_search_case_insensitive(self, avengers):
        """Test that search is case insensitive."""
        queryset = TeamLookup().search("AVENGERS", None)
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
        queryset = TeamLookup().search("super heroes", None)
        team_ids = list(queryset.values_list("id", flat=True))

        assert team.id in team_ids

    def test_search_partial_match(self, teen_titans):
        """Test searching with partial name match."""
        queryset = TeamLookup().search("titans", None)
        team_ids = list(queryset.values_list("id", flat=True))

        assert len(team_ids) == 1
        assert teen_titans.id in team_ids

    def test_search_no_match(self, teen_titans, avengers):
        """Test searching with no matching results."""
        queryset = TeamLookup().search("justice league", None)

        assert queryset.count() == 0

    def test_get_label_for_record(self, teen_titans):
        """Test that get_label_for_record returns string representation."""
        label = TeamLookup().label(teen_titans)

        assert isinstance(label, str)
        assert label == str(teen_titans)


class TestUniverseLookup:
    """Tests for UniverseLookup widget."""

    def test_search_by_name(self, earth_2_universe):
        """Test searching universes by name."""
        queryset = UniverseLookup().search("earth", None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert len(universe_ids) == 1
        assert earth_2_universe.id in universe_ids

    def test_search_by_designation(self, earth_2_universe):
        """Test searching universes by designation field."""
        queryset = UniverseLookup().search("Earth 2", None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert len(universe_ids) == 1
        assert earth_2_universe.id in universe_ids

    def test_search_case_insensitive(self, earth_2_universe):
        """Test that search is case insensitive."""
        queryset = UniverseLookup().search("EARTH", None)
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
        queryset = UniverseLookup().search("tierra-n", None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert universe.id in universe_ids

    def test_search_partial_match(self, earth_2_universe):
        """Test searching with partial name match."""
        queryset = UniverseLookup().search("2", None)
        universe_ids = list(queryset.values_list("id", flat=True))

        assert len(universe_ids) == 1
        assert earth_2_universe.id in universe_ids

    def test_search_no_match(self, earth_2_universe):
        """Test searching with no matching results."""
        queryset = UniverseLookup().search("earth-616", None)

        assert queryset.count() == 0

    def test_get_queryset_includes_publisher(self, earth_2_universe):
        """Test that get_queryset includes related publisher information."""
        queryset = UniverseLookup().get_base_queryset()
        universe = queryset.get(id=earth_2_universe.id)

        # Should have publisher prefetched (no additional queries)
        assert universe.publisher is not None
        assert universe.publisher.name == "DC Comics"

    def test_get_label_for_record(self, earth_2_universe):
        """Test that get_label_for_record includes the publisher name."""
        label = UniverseLookup().label(earth_2_universe)

        assert isinstance(label, str)
        assert label == f"{earth_2_universe} · {earth_2_universe.publisher.name}"


class TestImprintLookup:
    """Tests for ImprintLookup widget."""

    def test_search_by_name(self, vertigo_imprint, black_label_imprint):
        """Test searching imprints by name."""
        queryset = ImprintLookup().search("vertigo", None)
        imprint_ids = list(queryset.values_list("id", flat=True))

        assert len(imprint_ids) == 1
        assert vertigo_imprint.id in imprint_ids

    def test_search_case_insensitive(self, black_label_imprint):
        """Test that search is case insensitive."""
        queryset = ImprintLookup().search("BLACK LABEL", None)
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
        queryset = ImprintLookup().search("anos", None)
        imprint_ids = list(queryset.values_list("id", flat=True))

        assert imprint.id in imprint_ids

    def test_search_partial_match(self, vertigo_imprint):
        """Test searching with partial name match."""
        queryset = ImprintLookup().search("vert", None)
        imprint_ids = list(queryset.values_list("id", flat=True))

        assert len(imprint_ids) == 1
        assert vertigo_imprint.id in imprint_ids

    def test_search_no_match(self, vertigo_imprint, black_label_imprint):
        """Test searching with no matching results."""
        queryset = ImprintLookup().search("wildstorm", None)

        assert queryset.count() == 0

    def test_get_queryset_includes_publisher(self, vertigo_imprint):
        """Test that get_queryset includes related publisher information."""
        queryset = ImprintLookup().get_base_queryset()
        imprint = queryset.get(id=vertigo_imprint.id)

        # Should have publisher prefetched (no additional queries)
        assert imprint.publisher is not None
        assert imprint.publisher.name == "DC Comics"

    def test_get_label_for_record(self, vertigo_imprint):
        """Test that get_label_for_record includes the publisher name."""
        label = ImprintLookup().label(vertigo_imprint)

        assert isinstance(label, str)
        assert label == f"{vertigo_imprint} · {vertigo_imprint.publisher.name}"


@pytest.mark.django_db
class TestPublisherLabelQueries:
    """Tests that publisher labels don't cost a query per result."""

    @pytest.fixture(
        params=[
            (SeriesLookup, ("fc_series", "bat_sups_series"), "a"),
            (UniverseLookup, ("earth_2_universe",), "earth"),
            (ImprintLookup, ("vertigo_imprint", "black_label_imprint"), "e"),
        ],
        ids=["series", "universe", "imprint"],
    )
    def lookup_case(self, request):
        """Return a lookup, its records, and a query matching all of them."""
        lookup_class, fixture_names, query = request.param
        records = [request.getfixturevalue(name) for name in fixture_names]
        return lookup_class(), records, query

    def test_search_labels_use_one_query(self, lookup_case, django_assert_num_queries):
        """Test that labelling search results doesn't query each result's publisher."""
        lookup, records, query = lookup_case

        with django_assert_num_queries(1):
            items = [lookup.to_item(result) for result in lookup.search(query, None)]

        assert len(items) == len(records)

    def test_selected_labels_use_one_query(self, lookup_case, django_assert_num_queries):
        """Test that labelling selected values doesn't query each record's publisher."""
        lookup, records, _ = lookup_case
        keys = [str(record.pk) for record in records]

        with django_assert_num_queries(1):
            items = [lookup.to_item(result) for result in lookup.get_selected(keys)]

        assert len(items) == len(records)


@pytest.mark.django_db
class TestUnaccent:
    """Tests for the unaccent() helper."""

    def test_uses_postgres_rules(self):
        """Test that the query is unaccented by the same rules as the indexed field."""
        assert unaccent("Łódź Straße") == "Lodz Strasse"

    def test_ascii_text_skips_the_database(self, django_assert_num_queries):
        """Test that plain ASCII text is returned without a query."""
        with django_assert_num_queries(0):
            assert unaccent("Cameron") == "Cameron"


class TestLookupRanking:
    """Tests for the relevance order of lookup results."""

    @pytest.fixture
    def storm_characters(self, create_user):
        """Create characters that each match "storm" at a different tier."""
        user = create_user()
        return [
            Character.objects.create(name=name, slug=f"storm-{i}", edited_by=user, created_by=user)
            for i, name in enumerate(("Argos (Wildstorm)", "Acid Storm", "Stormavik", "Störm"))
        ]

    def test_closest_matches_come_first(self, storm_characters):
        """Test the whole name, then its start, then a word's start, then everything else."""
        names = [c.name for c in CharacterLookup().search("storm", None)]

        assert names == ["Störm", "Stormavik", "Acid Storm", "Argos (Wildstorm)"]

    def test_best_match_survives_max_results(self, storm_characters):
        """Test that the exact match isn't lost when the results are cut off."""
        cut_off = CharacterLookup().search("storm", None)[:1]

        assert [c.name for c in cut_off] == ["Störm"]

    def test_alias_match_stays_in_results(self, create_user, storm_characters):
        """Test that a record matching only on alias is still found, after the name matches."""
        user = create_user()
        Character.objects.create(
            name="Ororo Munroe",
            slug="ororo-munroe",
            alias=["Storm"],
            edited_by=user,
            created_by=user,
        )

        names = [c.name for c in CharacterLookup().search("storm", None)]

        assert names[-1] == "Ororo Munroe"

    def test_series_ties_keep_model_order(self, create_user, lookup_publisher, single_issue_type):
        """Test that equally ranked series stay in the model's order."""
        user = create_user()
        for name, year in (("Absolute Batman", 2024), ("Batman", 2016), ("Batman", 1940)):
            Series.objects.create(
                name=name,
                slug=f"batman-{year}",
                publisher=lookup_publisher,
                volume=year,
                year_began=year,
                series_type=single_issue_type,
                status=Series.Status.ONGOING,
                edited_by=user,
                created_by=user,
            )

        results = [(s.name, s.year_began) for s in SeriesLookup().search("batman", None)]

        assert results == [("Batman", 1940), ("Batman", 2016), ("Absolute Batman", 2024)]


class TestLookupSearchEndpoint:
    """Tests for searching through the izaya endpoint, as the widget does."""

    def test_returns_matching_options(self, client, create_user, spider_man_issue_1):
        client.force_login(create_user())
        resp = client.get(reverse("izaya:search", args=["IssueLookup"]), {"q": "Spider#1"})
        assert resp.status_code == HTTP_200_OK
        assert str(spider_man_issue_1).encode() in resp.content
        assert f'data-izaya-key="{spider_man_issue_1.pk}"'.encode() in resp.content

    def test_short_query_returns_no_options(self, client, create_user, spider_man_issue_1):
        client.force_login(create_user())
        resp = client.get(reverse("izaya:search", args=["IssueLookup"]), {"q": "sp"})
        assert resp.status_code == HTTP_200_OK
        assert b"data-izaya-key" not in resp.content

    def test_anonymous_search_is_denied(self, client, spider_man_issue_1):
        resp = client.get(reverse("izaya:search", args=["IssueLookup"]), {"q": "Spider#1"})
        assert resp.status_code == HTTP_403_FORBIDDEN
        assert resp.headers["X-Izaya-Denied"] == "true"
        assert b"data-izaya-key" not in resp.content

    @pytest.mark.parametrize("lookup", sorted(registry))
    def test_every_lookup_denies_anonymous_searches(self, client, lookup):
        resp = client.get(reverse("izaya:search", args=[lookup]), {"q": "Spider"})
        assert resp.status_code == HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", ["pull-list:detail", "wish-list:detail"])
def test_page_with_lookup_widget_loads_its_script(client, create_user, test_password, url_name):
    """The base template loads the script once, so pages don't include the form's media."""
    user = create_user()
    client.login(username=user.username, password=test_password)
    resp = client.get(reverse(url_name))
    assert resp.status_code == HTTP_200_OK
    assert resp.content.count(b"izaya/izaya.js") == 1
