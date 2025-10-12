import uuid
from datetime import date, datetime

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.utils import timezone

from comicsdb.models import Announcement, Credits, Imprint, Universe
from comicsdb.models.arc import Arc
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Role
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series, SeriesType
from comicsdb.models.team import Team
from users.models import CustomUser

NUMBER_OF_ISSUES = 35


@pytest.fixture
def test_password():
    return "strong-test-pass"


@pytest.fixture
def test_email():
    return "foo@bar.com"


@pytest.fixture
def create_user(db, test_password, test_email):
    def make_user(**kwargs):
        kwargs["password"] = test_password
        kwargs["email"] = test_email
        if "username" not in kwargs:
            kwargs["username"] = str(uuid.uuid4())
        return CustomUser.objects.create_user(**kwargs)

    return make_user


@pytest.fixture
def create_editor_group(db):
    group, _ = Group.objects.get_or_create(name="editors")
    models = [
        Arc,
        Character,
        Creator,
        Credits,
        Imprint,
        Issue,
        Publisher,
        Series,
        Team,
        Universe,
    ]
    for model in models:
        ct = ContentType.objects.get_for_model(model)
        perms = Permission.objects.filter(content_type=ct)
        for perm in perms:
            if "add" in perm.codename:
                group.permissions.add(perm)
            if "change" in perm.codename:
                group.permissions.add(perm)
    return group


@pytest.fixture
def create_staff_user(create_user, create_editor_group):
    user: CustomUser = create_user()
    user.is_staff = True
    user.groups.add(create_editor_group)
    user.save()
    return user


@pytest.fixture
def auto_login_user(db, client, create_user, test_password):
    def make_auto_login(user=None):
        if user is None:
            user = create_user()
        client.login(username=user.username, password=test_password)
        return client, user

    return make_auto_login


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def api_client_with_credentials(db, create_user, api_client):
    user = create_user()
    api_client.force_authenticate(user=user)
    yield api_client
    api_client.force_authenticate(user=None)


@pytest.fixture
def api_client_with_staff_credentials(db, create_staff_user, api_client):
    api_client.force_authenticate(user=create_staff_user)
    yield api_client
    api_client.force_authenticate(user=None)


@pytest.fixture
def wwh_arc(create_user):
    user = create_user()
    return Arc.objects.create(
        name="World War Hulk", slug="world-war-hulk", edited_by=user, created_by=user
    )


@pytest.fixture
def fc_arc(create_user):
    user = create_user()
    return Arc.objects.create(
        name="Final Crisis", slug="final-crisis", edited_by=user, created_by=user
    )


@pytest.fixture
def dc_comics(create_user):
    user = create_user()
    return Publisher.objects.create(
        name="DC Comics", slug="dc-comics", edited_by=user, created_by=user
    )


@pytest.fixture
def marvel(create_user):
    user = create_user()
    return Publisher.objects.create(name="Marvel", slug="marvel", edited_by=user, created_by=user)


@pytest.fixture
def vertigo_imprint(create_user, dc_comics):
    user = create_user()
    return Imprint.objects.create(
        name="Vertigo", slug="vertigo", publisher=dc_comics, edited_by=user, created_by=user
    )


@pytest.fixture
def black_label_imprint(create_user, dc_comics):
    user = create_user()
    return Imprint.objects.create(
        name="Black Label",
        slug="black-label",
        publisher=dc_comics,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def earth_2_universe(create_user, dc_comics):
    desc = "Home to modernized versions of the Justice Society of Earth."
    user = create_user()
    return Universe.objects.create(
        publisher=dc_comics,
        name="Earth 2",
        slug="earth-2",
        designation="Earth 2",
        desc=desc,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("loaddata", "../../comicsdb/fixtures/series_type.yaml")


@pytest.fixture
def single_issue_type(db):
    return SeriesType.objects.get(name__icontains="single")


@pytest.fixture
def fc_series(create_user, dc_comics, single_issue_type):
    user = create_user()
    return Series.objects.create(
        name="Final Crisis",
        slug="final-crisis",
        publisher=dc_comics,
        volume="1",
        year_began=1939,
        series_type=single_issue_type,
        status=Series.Status.CANCELLED,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def bat_sups_series(create_user, dc_comics, single_issue_type):
    user = create_user()
    return Series.objects.create(
        name="Batman / Superman",
        slug="batman-superman",
        publisher=dc_comics,
        volume="1",
        year_began=2016,
        series_type=single_issue_type,
        status=Series.Status.CANCELLED,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def sandman_series(create_user, dc_comics, vertigo_imprint, single_issue_type):
    user = create_user()
    return Series.objects.create(
        name="Sandman",
        slug="sandman",
        publisher=dc_comics,
        imprint=vertigo_imprint,
        volume=1,
        year_began=1989,
        series_type=single_issue_type,
        status=Series.Status.CANCELLED,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def issue_with_arc(create_user, fc_series, fc_arc, superman):
    user = create_user()
    i = Issue.objects.create(
        series=fc_series,
        number="1",
        slug="final-crisis-1",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
    i.arcs.add(fc_arc)
    i.characters.add(superman)
    return i


@pytest.fixture
def basic_issue(create_user, fc_series):
    user = create_user()
    return Issue.objects.create(
        series=fc_series,
        number="1",
        slug="final-crisis-1",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def list_of_issues(create_user, fc_series):
    user = create_user()

    # Create the store date for this week
    year, week, _ = date.today().isocalendar()
    # The "3" is the weekday (Wednesday)
    wednesday = f"{year}-{week}-3"
    # Dates used in Issue creating
    in_store_date = datetime.strptime(wednesday, "%G-%V-%u")
    cover_date = date.today()

    for i_num in range(NUMBER_OF_ISSUES):
        Issue.objects.create(
            series=fc_series,
            number=i_num,
            slug=f"final-crisis-1939-{i_num}",
            cover_date=cover_date,
            store_date=in_store_date,
            edited_by=user,
            created_by=user,
        )


@pytest.fixture
def superman(create_user):
    user = create_user()
    return Character.objects.create(
        name="Superman", slug="superman", edited_by=user, created_by=user
    )


@pytest.fixture
def batman(create_user):
    user = create_user()
    return Character.objects.create(name="Batman", slug="batman", edited_by=user, created_by=user)


@pytest.fixture
def john_byrne(create_user):
    user = create_user()
    return Creator.objects.create(
        name="John Byrne", slug="john-byrne", edited_by=user, created_by=user
    )


@pytest.fixture
def walter_simonson(create_user):
    user = create_user()
    return Creator.objects.create(
        name="Walter Simonson", slug="walter-simonson", edited_by=user, created_by=user
    )


@pytest.fixture
def teen_titans(create_user):
    user = create_user()
    return Team.objects.create(
        name="Teen Titans", slug="teen-titans", edited_by=user, created_by=user
    )


@pytest.fixture
def avengers(create_user):
    user = create_user()
    return Team.objects.create(
        name="The Avengers", slug="the-avengers", edited_by=user, created_by=user
    )


@pytest.fixture
def writer(db):
    return Role.objects.create(name="Writer", notes="Nothing here.", order=20)


@pytest.fixture
def announcement(db):
    return Announcement.objects.create(
        title="Test Announcement", content="Nothing here.", active=True
    )


@pytest.fixture
def trade_paperback_type(db):
    return SeriesType.objects.get(name="Trade Paperback")


@pytest.fixture
def omnibus_type(db):
    return SeriesType.objects.get(name="Omnibus")


@pytest.fixture
def hardcover_type(db):
    return SeriesType.objects.get(name="Hardcover")


@pytest.fixture
def tpb_series(create_user, dc_comics, trade_paperback_type):
    """Create a Trade Paperback series."""
    user = create_user()
    return Series.objects.create(
        name="Batman: Year One",
        slug="batman-year-one-tp",
        publisher=dc_comics,
        volume="1",
        year_began=2005,
        series_type=trade_paperback_type,
        status=Series.Status.COMPLETED,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def omnibus_series(create_user, marvel, omnibus_type):
    """Create an Omnibus series."""
    user = create_user()
    return Series.objects.create(
        name="Spider-Man Omnibus",
        slug="spider-man-omnibus",
        publisher=marvel,
        volume="1",
        year_began=2020,
        series_type=omnibus_type,
        status=Series.Status.COMPLETED,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def hardcover_series(create_user, dc_comics, hardcover_type):
    """Create a Hardcover series."""
    user = create_user()
    return Series.objects.create(
        name="Absolute Batman",
        slug="absolute-batman",
        publisher=dc_comics,
        volume="1",
        year_began=2015,
        series_type=hardcover_type,
        status=Series.Status.COMPLETED,
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def single_story_issue(create_user, fc_series, superman, batman):
    """Create an issue with one story title and characters."""
    user = create_user()
    issue = Issue.objects.create(
        series=fc_series,
        number="2",
        slug="final-crisis-2",
        name=["The Beginning"],
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
    issue.characters.add(superman, batman)
    return issue


@pytest.fixture
def multi_story_issue(create_user, fc_series, superman, teen_titans):
    """Create an issue with multiple story titles."""
    user = create_user()
    issue = Issue.objects.create(
        series=fc_series,
        number="3",
        slug="final-crisis-3",
        name=["Story One", "Story Two", "Story Three"],
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
    issue.characters.add(superman)
    issue.teams.add(teen_titans)
    return issue


@pytest.fixture
def no_story_issue(create_user, fc_series, batman, avengers):
    """Create an issue with no story titles."""
    user = create_user()
    issue = Issue.objects.create(
        series=fc_series,
        number="4",
        slug="final-crisis-4",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
    issue.characters.add(batman)
    issue.teams.add(avengers)
    return issue


@pytest.fixture
def tpb_issue(create_user, tpb_series):
    """Create a Trade Paperback issue without characters or teams."""
    user = create_user()
    return Issue.objects.create(
        series=tpb_series,
        number="1",
        slug="batman-year-one-tp-1",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def omnibus_issue(create_user, omnibus_series):
    """Create an Omnibus issue without characters or teams."""
    user = create_user()
    return Issue.objects.create(
        series=omnibus_series,
        number="1",
        slug="spider-man-omnibus-1",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )


@pytest.fixture
def hardcover_issue(create_user, hardcover_series):
    """Create a Hardcover issue without characters or teams."""
    user = create_user()
    return Issue.objects.create(
        series=hardcover_series,
        number="1",
        slug="absolute-batman-1",
        cover_date=timezone.now().date(),
        edited_by=user,
        created_by=user,
    )
