import json
from datetime import date

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from comicsdb.management.commands.invalid_upcs import match_title_code, repair_upc
from comicsdb.models.arc import Arc
from comicsdb.models.attribution import Attribution
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Credits, Role
from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from comicsdb.models.team import Team
from comicsdb.models.universe import Universe
from comicsdb.models.variant import Variant
from users.models import CustomUser

FAKE_DESC = "Duplicate Object"
FAKE_ALIAS = ["Clark Kent"]


@pytest.fixture
def other_character(create_user) -> Character:
    user = create_user()
    supes = Character.objects.create(
        name="Superman",
        desc=FAKE_DESC,
        alias=FAKE_ALIAS,
        edited_by=user,
        created_by=user,
    )
    at1 = Attribution(source="W", url="https://foo.com")
    at2 = Attribution(source="M", url="https://marvel.com/foo")
    supes.attribution.add(at1, bulk=False)
    supes.attribution.add(at2, bulk=False)
    return supes


def test_merge_characters(
    superman: Character, other_character: Character, basic_issue: Issue
) -> None:
    assert other_character.attribution.count() == 2
    basic_issue.characters.add(other_character)
    call_command("merge_characters", canonical=superman.id, other=other_character.id)
    superman.refresh_from_db()
    basic_issue.refresh_from_db()
    assert superman.desc == FAKE_DESC
    assert superman.alias == FAKE_ALIAS
    assert superman in basic_issue.characters.all()
    assert superman.attribution.count() == 0


@pytest.fixture
def other_arc(create_user) -> Arc:
    user = create_user()
    return Arc.objects.create(name="Final Crisis", desc=FAKE_DESC, edited_by=user, created_by=user)


def test_merge_arcs(fc_arc: Arc, other_arc: Arc, basic_issue: Issue) -> None:
    basic_issue.arcs.add(other_arc)
    call_command("merge_arcs", canonical=fc_arc.id, other=other_arc.id)
    fc_arc.refresh_from_db()
    basic_issue.refresh_from_db()
    assert fc_arc.desc == FAKE_DESC
    assert fc_arc in basic_issue.arcs.all()


@pytest.fixture
def other_team(create_user) -> Team:
    user = create_user()
    return Team.objects.create(name="Teen Titans", desc=FAKE_DESC, edited_by=user, created_by=user)


def test_merge_teams(teen_titans: Team, other_team: Team, basic_issue: Issue) -> None:
    basic_issue.teams.add(other_team)
    call_command("merge_teams", canonical=teen_titans.id, other=other_team.id)
    teen_titans.refresh_from_db()
    basic_issue.refresh_from_db()
    assert teen_titans.desc == FAKE_DESC
    assert teen_titans in basic_issue.teams.all()


@pytest.fixture
def other_creator(create_user) -> Creator:
    user = create_user()
    return Creator.objects.create(name="John Byre", desc=FAKE_DESC, edited_by=user, created_by=user)


def test_merge_creators(
    john_byrne: Creator, other_creator: Creator, basic_issue: Issue, writer: Role
) -> None:
    credit_obj = Credits.objects.create(issue=basic_issue, creator=other_creator)
    credit_obj.role.add(writer)
    call_command("merge_creators", canonical=john_byrne.id, other=other_creator.id)
    john_byrne.refresh_from_db()
    credit_obj.refresh_from_db()
    assert john_byrne.desc == FAKE_DESC
    assert credit_obj.creator == john_byrne


# Tests for add_universe_to_series management command


@pytest.fixture
def system_user(db):
    """Get the system user with id=1 (created in django_db_setup)."""
    return CustomUser.objects.get(id=1)


@pytest.fixture
def marvel_universe(create_user, marvel):
    """Create a Marvel Universe."""
    user = create_user()
    return Universe.objects.create(
        publisher=marvel,
        name="Earth-616",
        slug="earth-616",
        designation="Earth-616",
        desc="Main Marvel Universe continuity",
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def series_with_issues(create_user, marvel, single_issue_type, superman, batman):
    """Create a series with multiple issues and characters."""
    user = create_user()
    series = Series.objects.create(
        name="Test Series",
        slug="test-series",
        publisher=marvel,
        volume="1",
        year_began=2020,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )
    # Create 3 issues for this series
    for i in range(1, 4):
        issue = Issue.objects.create(
            series=series,
            number=str(i),
            slug=f"test-series-{i}",
            cover_date=timezone.now().date(),
            edited_by=user,
            created_by=user,
        )
        # Add characters to issues
        issue.characters.add(superman, batman)
    return series


@pytest.fixture
def series_with_universe(create_user, marvel, single_issue_type, marvel_universe):
    """Create a series with an issue that already has a universe."""
    user = create_user()
    series = Series.objects.create(
        name="Existing Universe Series",
        slug="existing-universe-series",
        publisher=marvel,
        volume="1",
        year_began=2021,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )
    issue = Issue.objects.create(
        series=series,
        number="1",
        slug="existing-universe-series-1",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
    issue.universes.add(marvel_universe)
    return series


def test_add_universe_to_series_basic(
    system_user, series_with_issues: Series, marvel_universe: Universe
):
    """Test adding a universe to all issues in a series."""
    # Verify initial state - no universes
    for issue in series_with_issues.issues.all():
        assert issue.universes.count() == 0

    # Run the command
    call_command(
        "add_universe_to_series", series=series_with_issues.id, universe=marvel_universe.id
    )

    # Verify universe was added to all issues
    for issue in series_with_issues.issues.all():
        issue.refresh_from_db()
        assert marvel_universe in issue.universes.all()
        assert issue.universes.count() == 1


def test_add_universe_to_series_updates_edited_by(
    system_user, series_with_issues: Series, marvel_universe: Universe
):
    """Test that the edited_by field is set to system user."""
    call_command(
        "add_universe_to_series", series=series_with_issues.id, universe=marvel_universe.id
    )

    # Verify edited_by was updated
    for issue in series_with_issues.issues.all():
        issue.refresh_from_db()
        assert issue.edited_by == system_user


def test_add_universe_to_series_creates_history(
    system_user, series_with_issues: Series, marvel_universe: Universe
):
    """Test that history records are created with change reason."""
    call_command(
        "add_universe_to_series", series=series_with_issues.id, universe=marvel_universe.id
    )

    # Verify history was created
    for issue in series_with_issues.issues.all():
        issue.refresh_from_db()
        history = issue.history.first()
        assert history is not None
        assert f"Added universe '{marvel_universe}'" in history.history_change_reason


def test_add_universe_to_series_with_characters(
    system_user,
    series_with_issues: Series,
    marvel_universe: Universe,
    superman: Character,
    batman: Character,
):
    """Test adding universe to characters when --characters flag is used."""
    # Verify initial state - characters have no universes
    assert superman.universes.count() == 0
    assert batman.universes.count() == 0

    # Run the command with --characters flag
    call_command(
        "add_universe_to_series",
        series=series_with_issues.id,
        universe=marvel_universe.id,
        characters=True,
    )

    # Verify universe was added to all characters
    superman.refresh_from_db()
    batman.refresh_from_db()
    assert marvel_universe in superman.universes.all()
    assert marvel_universe in batman.universes.all()


def test_add_universe_to_series_characters_no_duplicates(
    system_user, series_with_issues: Series, marvel_universe: Universe, superman: Character
):
    """Test that characters appearing in multiple issues are only processed once."""
    # Run the command with --characters flag
    call_command(
        "add_universe_to_series",
        series=series_with_issues.id,
        universe=marvel_universe.id,
        characters=True,
    )

    # Verify universe was added only once
    superman.refresh_from_db()
    assert superman.universes.count() == 1
    assert marvel_universe in superman.universes.all()


def test_add_universe_to_series_characters_updates_edited_by(
    system_user, series_with_issues: Series, marvel_universe: Universe, superman: Character
):
    """Test that character edited_by field is updated to system user."""
    call_command(
        "add_universe_to_series",
        series=series_with_issues.id,
        universe=marvel_universe.id,
        characters=True,
    )

    superman.refresh_from_db()
    assert superman.edited_by == system_user


def test_add_universe_to_series_characters_creates_history(
    system_user, series_with_issues: Series, marvel_universe: Universe, superman: Character
):
    """Test that character history records are created with change reason."""
    call_command(
        "add_universe_to_series",
        series=series_with_issues.id,
        universe=marvel_universe.id,
        characters=True,
    )

    superman.refresh_from_db()
    history = superman.history.first()
    assert history is not None
    assert f"Added universe '{marvel_universe}'" in history.history_change_reason


def test_add_universe_to_series_skips_existing_universe(
    system_user, series_with_universe: Series, marvel_universe: Universe
):
    """Test that issues already having the universe are skipped."""
    issue = series_with_universe.issues.first()
    initial_universe_count = issue.universes.count()

    # Run the command
    call_command(
        "add_universe_to_series", series=series_with_universe.id, universe=marvel_universe.id
    )

    # Verify universe count didn't change
    issue.refresh_from_db()
    assert issue.universes.count() == initial_universe_count


def test_add_universe_to_series_invalid_series_id(system_user, marvel_universe: Universe):
    """Test that CommandError is raised for non-existent series."""
    with pytest.raises(CommandError, match="Series with id 99999 does not exist"):
        call_command("add_universe_to_series", series=99999, universe=marvel_universe.id)


def test_add_universe_to_series_invalid_universe_id(system_user, series_with_issues: Series):
    """Test that CommandError is raised for non-existent universe."""
    with pytest.raises(CommandError, match="Universe with id 99999 does not exist"):
        call_command("add_universe_to_series", series=series_with_issues.id, universe=99999)


def test_add_universe_to_series_empty_series(
    system_user, create_user, dc_comics, single_issue_type, earth_2_universe
):
    """Test handling of series with no issues."""
    user = create_user()
    empty_series = Series.objects.create(
        name="Empty Series",
        slug="empty-series",
        publisher=dc_comics,
        volume="1",
        year_began=2022,
        series_type=single_issue_type,
        status=Series.Status.ONGOING,
        edited_by=user,
        created_by=user,
    )

    # Should not raise error, just exit gracefully
    call_command("add_universe_to_series", series=empty_series.id, universe=earth_2_universe.id)


@pytest.fixture
def upc_issues(series_with_issues: Series) -> list[Issue]:
    """Give the series' issues one valid and two invalid UPCs, bypassing validation."""
    issues = list(series_with_issues.issues.order_by("number"))
    for issue, upc in zip(issues, ["76194137738400111", "0716585646802", "UPC 123"], strict=True):
        Issue.objects.filter(pk=issue.pk).update(upc=upc)
    return issues


@pytest.fixture
def upc_variants(upc_issues: list[Issue]) -> list[Variant]:
    return [
        Variant.objects.create(issue=upc_issues[0], image="variants/a.jpg", upc="123456789012"),
        Variant.objects.create(issue=upc_issues[0], image="variants/b.jpg", upc="12345"),
    ]


def test_invalid_upcs_dry_run(system_user, upc_issues, upc_variants, tmp_path):
    output = tmp_path / "upcs.json"
    call_command("invalid_upcs", output=output)

    data = json.loads(output.read_text())
    assert [(i["id"], i["upc"], i["reason"]) for i in data["issues"]] == [
        (upc_issues[1].pk, "0716585646802", "upc_invalid_check_digit"),
        (upc_issues[2].pk, "UPC 123", "upc_not_numeric"),
    ]
    assert [(v["id"], v["reason"]) for v in data["variants"]] == [
        (upc_variants[1].pk, "upc_invalid_length")
    ]
    # Nothing is cleared without --clear.
    assert Issue.objects.get(pk=upc_issues[1].pk).upc == "0716585646802"
    assert Variant.objects.get(pk=upc_variants[1].pk).upc == "12345"


def test_invalid_upcs_clear(system_user, upc_issues, upc_variants, tmp_path):
    before = {i.pk: Issue.objects.get(pk=i.pk).modified for i in upc_issues}
    call_command("invalid_upcs", output=tmp_path / "upcs.json", clear=True)

    valid, bad_check, non_numeric = (Issue.objects.get(pk=i.pk) for i in upc_issues)
    assert valid.upc == "76194137738400111"
    assert bad_check.upc == ""
    assert non_numeric.upc == ""
    assert bad_check.edited_by == system_user
    assert bad_check.modified > before[bad_check.pk]
    assert bad_check.history.first().history_change_reason == (
        "Cleared invalid UPC '0716585646802' (upc_invalid_check_digit)"
    )
    # The valid issue's modified is bumped because one of its variants was cleared.
    assert valid.modified > before[valid.pk]

    assert Variant.objects.get(pk=upc_variants[0].pk).upc == "123456789012"
    assert Variant.objects.get(pk=upc_variants[1].pk).upc == ""


@pytest.mark.parametrize(
    ("upc", "cover_date", "expected"),
    [
        # Values confirmed against cover images.
        ("596060471656311", date(2008, 8, 1), "75960604716156311"),
        ("7619413574401011", date(2019, 6, 1), "76194135744701011"),
        ("8442840030902511", date(2015, 2, 1), "84428400309402511"),
        ("759606092681003111", date(2021, 10, 1), "75960609268003111"),
        ("071486024512", date(1976, 12, 1), None),
        ("123456789012345", date(2009, 1, 1), None),
        ("761941296330000711", date(2011, 7, 1), None),
        ("759606092691003111", date(2021, 10, 1), None),
        ("59606014150011X", date(2009, 1, 1), None),
        ("5960601415001", date(2009, 1, 1), None),
    ],
    ids=[
        "marvel_15_digit",
        "16_digit_missing_check_digit",
        "16_digit_missing_check_digit_other_publisher",
        "marvel_18_digit_stray_digit",
        "legacy_already_has_leading_zero",
        "15_digit_not_marvel",
        "18_digit_not_marvel",
        "marvel_18_digit_still_invalid",
        "not_numeric",
        "unrecognized_length",
    ],
)
def test_repair_upc(upc, cover_date, expected):
    assert repair_upc(upc, cover_date) == expected


# Values confirmed against cover images.
IRON_MAN_93 = ("071486024512", date(1976, 12, 1))  # '0714860245412'
WEIRD_WAR_TALES_82 = ("709893071712", date(1979, 12, 1))  # '0709893071712'


@pytest.mark.parametrize(
    ("upc", "cover_date", "title_codes", "expected"),
    [
        (*WEIRD_WAR_TALES_82, {"07098930717"}, "0709893071712"),
        (*WEIRD_WAR_TALES_82, set(), None),
        ("709893071712", date(1979, 11, 1), {"07098930717"}, None),
        ("709893071712", date(1993, 12, 1), {"07098930717"}, None),
        # Sad Sack and the Sarge #152: '718' is also a typo for the series' '716'.
        ("718585186412", date(1981, 12, 1), {"07165851864"}, None),
        (*IRON_MAN_93, {"07148602454"}, "0714860245412"),
        (*IRON_MAN_93, {"07148602454", "07148602462"}, "0714860245412"),
        # Archie Giant Series #455: two of the series' title codes match.
        ("027100069901", date(1977, 1, 1), {"02710006989", "02710006991"}, None),
        (*IRON_MAN_93, {"07148602462"}, None),
        (*IRON_MAN_93, set(), None),
        ("071486024512", date(1976, 11, 1), {"07148602454"}, None),
    ],
    ids=[
        "leading_zero",
        "leading_zero_no_title_codes",
        "leading_zero_wrong_month",
        "leading_zero_too_recent",
        "leading_zero_title_code_mismatch",
        "title_code_match",
        "title_code_match_among_others",
        "title_code_ambiguous",
        "title_code_no_match",
        "title_code_no_title_codes",
        "title_code_wrong_month",
    ],
)
def test_repair_upc_legacy_12_digit(upc, cover_date, title_codes, expected):
    assert repair_upc(upc, cover_date, title_codes) == expected


def test_match_title_code():
    assert match_title_code("0714860245", {"07148602454", "07098930410"}) == "07148602454"


def test_invalid_upcs_clear_repairs_known_formats(system_user, upc_issues, upc_variants, tmp_path):
    legacy_issue, marvel_issue = upc_issues[1], upc_issues[2]
    # A legacy 13 digit UPC without a check digit is valid on an issue from before 1993.
    Issue.objects.filter(pk=legacy_issue.pk).update(cover_date=date(1979, 2, 1))
    Issue.objects.filter(pk=marvel_issue.pk).update(upc="596060141500111")
    Variant.objects.filter(pk=upc_variants[1].pk).update(upc="596060141500211")
    output = tmp_path / "upcs.json"

    call_command("invalid_upcs", output=output, clear=True)

    data = json.loads(output.read_text())
    assert [(i["id"], i["repaired_upc"]) for i in data["issues"]] == [
        (marvel_issue.pk, "75960601415600111")
    ]
    assert Issue.objects.get(pk=legacy_issue.pk).upc == "0716585646802"
    marvel_issue.refresh_from_db()
    assert marvel_issue.upc == "75960601415600111"
    assert marvel_issue.history.first().history_change_reason == (
        "Repaired UPC '596060141500111' (upc_invalid_check_digit)"
    )
    assert Variant.objects.get(pk=upc_variants[1].pk).upc == "75960601415600211"


def test_invalid_upcs_clear_restores_title_code_from_series(system_user, upc_issues, tmp_path):
    sibling, truncated = upc_issues[1], upc_issues[2]
    # The sibling's legacy UPC gives the series' title code, '07165856468'.
    Issue.objects.filter(pk=sibling.pk).update(cover_date=date(1979, 2, 1))
    Issue.objects.filter(pk=truncated.pk).update(cover_date=date(1979, 4, 1), upc="071658564604")

    call_command("invalid_upcs", output=tmp_path / "upcs.json", clear=True)

    assert Issue.objects.get(pk=truncated.pk).upc == "0716585646804"
