import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from comicsdb.models.arc import Arc
from comicsdb.models.attribution import Attribution
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Credits, Role
from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from comicsdb.models.team import Team
from comicsdb.models.universe import Universe
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
