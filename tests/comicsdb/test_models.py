from comicsdb.models import (
    Announcement,
    Arc,
    Character,
    Creator,
    Imprint,
    Issue,
    Publisher,
    Rating,
    Role,
    Series,
    SeriesType,
    Team,
    Universe,
)
from comicsdb.models.common import generate_slug_from_name
from comicsdb.models.genre import Genre

HTTP_200_OK = 200


def test_announcement_model(announcement):
    assert isinstance(announcement, Announcement)
    assert announcement.active
    assert announcement.active_announcements()


def test_team_creation(avengers):
    assert isinstance(avengers, Team)
    assert str(avengers) == avengers.name
    # test generate slug function
    new_slug = generate_slug_from_name(avengers)
    expected_slug = f"{avengers.slug}-1"
    assert new_slug == expected_slug


def test_team_verbose_name_plural(avengers):
    assert str(avengers._meta.verbose_name_plural) == "teams"


def test_team_absolute_url(auto_login_user, avengers):
    client, _ = auto_login_user()
    resp = client.get(avengers.get_absolute_url())
    assert resp.status_code == HTTP_200_OK


def test_character_creation(batman):
    assert isinstance(batman, Character)
    assert str(batman) == batman.name


def test_character_verbose_name_plural(batman):
    assert str(batman._meta.verbose_name_plural) == "characters"


def test_character_absolute_url(auto_login_user, batman):
    client, _ = auto_login_user()
    resp = client.get(batman.get_absolute_url())
    assert resp.status_code == HTTP_200_OK


def test_arc_creation(wwh_arc):
    assert isinstance(wwh_arc, Arc)
    assert str(wwh_arc) == wwh_arc.name


def test_arc_verbose_name_plural(wwh_arc):
    assert str(wwh_arc._meta.verbose_name_plural) == "arcs"


def test_arc_absolute_url(auto_login_user, wwh_arc):
    client, _ = auto_login_user()
    resp = client.get(wwh_arc.get_absolute_url())
    assert resp.status_code == HTTP_200_OK


def test_creator_creation(john_byrne):
    assert isinstance(john_byrne, Creator)
    assert str(john_byrne) == john_byrne.name


def test_creator_get_full_name(john_byrne):
    assert john_byrne.name == john_byrne.name


def test_creator_verbose_name_plural(john_byrne):
    assert str(john_byrne._meta.verbose_name_plural) == "creators"


def test_creator_absolute_url(auto_login_user, john_byrne):
    client, _ = auto_login_user()
    resp = client.get(john_byrne.get_absolute_url())
    assert resp.status_code == HTTP_200_OK


def test_role_creation(writer):
    assert isinstance(writer, Role)
    assert str(writer) == writer.name


def test_role_verbose_name_plural(writer):
    assert str(writer._meta.verbose_name_plural) == "roles"


def test_publisher_series_count(dc_comics, fc_series):
    assert dc_comics.series_count == 1


def test_publisher_creation(dc_comics):
    assert isinstance(dc_comics, Publisher)
    assert str(dc_comics) == dc_comics.name


def test_publisher_verbose_name_plural(dc_comics):
    assert str(dc_comics._meta.verbose_name_plural) == "publishers"


def test_publisher_absolute_url(auto_login_user, dc_comics):
    client, _ = auto_login_user()
    resp = client.get(dc_comics.get_absolute_url())
    assert resp.status_code == HTTP_200_OK


def test_imprint_series_count(vertigo_imprint, sandman_series):
    assert vertigo_imprint.series_count == 1


def test_imprint_creation(vertigo_imprint):
    assert isinstance(vertigo_imprint, Imprint)
    assert str(vertigo_imprint) == vertigo_imprint.name


def test_imprint_verbose_name_plural(vertigo_imprint):
    assert str(vertigo_imprint._meta.verbose_name_plural) == "imprints"


def test_imprint_absolute_url(auto_login_user, vertigo_imprint):
    client, _ = auto_login_user()
    resp = client.get(vertigo_imprint.get_absolute_url())
    assert resp.status_code == HTTP_200_OK


def test_series_creation(fc_series):
    assert isinstance(fc_series, Series)
    assert str(fc_series), "Final Crisis (1939)"


def test_series_verbose_name_plural(fc_series):
    assert str(fc_series._meta.verbose_name_plural) == "Series"


def test_series_absolute_url(auto_login_user, fc_series):
    client, _ = auto_login_user()
    resp = client.get(fc_series.get_absolute_url())
    assert resp.status_code == HTTP_200_OK


def test_issue_creation(issue_with_arc):
    assert isinstance(issue_with_arc, Issue)
    assert str(issue_with_arc) == "Final Crisis (1939) #1"


def test_issue_verbose_name_plural(issue_with_arc):
    assert str(issue_with_arc._meta.verbose_name_plural) == "issues"


def test_issue_absolute_url(auto_login_user, issue_with_arc):
    client, _ = auto_login_user()
    resp = client.get(issue_with_arc.get_absolute_url())
    assert resp.status_code == HTTP_200_OK


# This test should be in the SeriesTest but for now let's leave this here.
def test_issue_count(issue_with_arc, superman):
    issue_count = superman.issue_count
    assert issue_count == 1


def test_seriestype_creation(single_issue_type):
    assert isinstance(single_issue_type, SeriesType)
    assert str(single_issue_type) == single_issue_type.name


def test_fantasy_genre(db):
    fantasy = Genre.objects.get(name="Fantasy")
    assert isinstance(fantasy, Genre)


def test_unknown_rating(db):
    unknown = Rating.objects.get(name="Unknown")
    assert isinstance(unknown, Rating)


def test_universe_creation(earth_2_universe):
    assert isinstance(earth_2_universe, Universe)
    assert str(earth_2_universe) == "Earth 2"


def test_universe_verbose_name_plural(earth_2_universe):
    assert str(earth_2_universe._meta.verbose_name_plural) == "universes"


def test_universe_absolute_url(auto_login_user, earth_2_universe):
    client, _ = auto_login_user()
    resp = client.get(earth_2_universe.get_absolute_url())
    assert resp.status_code == HTTP_200_OK
