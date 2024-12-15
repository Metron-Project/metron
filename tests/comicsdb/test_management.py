import pytest
from django.core.management import call_command

from comicsdb.models.arc import Arc
from comicsdb.models.attribution import Attribution
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Credits, Role
from comicsdb.models.issue import Issue
from comicsdb.models.team import Team

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
    return Arc.objects.create(
        name="Final Crisis", desc=FAKE_DESC, edited_by=user, created_by=user
    )


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
    return Team.objects.create(
        name="Teen Titans", desc=FAKE_DESC, edited_by=user, created_by=user
    )


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
    return Creator.objects.create(
        name="John Byre", desc=FAKE_DESC, edited_by=user, created_by=user
    )


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
