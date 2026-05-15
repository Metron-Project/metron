import operator
from functools import reduce
from urllib.parse import quote_plus

import pytest
from django.db.models import Count, Q
from django.urls import reverse
from rest_framework import status

from api.v1_0.serializers import SeriesListSerializer
from comicsdb.models import Credits, Series
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Role
from comicsdb.models.imprint import Imprint
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import SeriesType
from comicsdb.models.team import Team
from comicsdb.models.universe import Universe


@pytest.fixture
def create_series_data(single_issue_type: SeriesType, dc_comics: Publisher):
    return {
        "name": "The Wasp",
        "sort_name": "Wasp",
        "volume": 1,
        "desc": "Cancelled series starring the Wasp",
        "year_began": 2023,
        "series_type": single_issue_type.id,
        "status": Series.Status.COMPLETED,
        "publisher": dc_comics.id,
        "imprint": "",  # Empty string or Imprint ID
    }


@pytest.fixture
def create_put_data():
    return {
        "name": "Wasp",
    }


# Post tests
def test_unauthorized_post_url(db, api_client, create_series_data):
    resp = api_client.post(reverse("api:series-list"), data=create_series_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_series_data):
    resp = api_client_with_credentials.post(reverse("api:series-list"), data=create_series_data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_admin_user_post_url(db, api_client_with_staff_credentials, create_series_data):
    resp = api_client_with_staff_credentials.post(
        reverse("api:series-list"), data=create_series_data
    )
    assert resp.status_code == status.HTTP_201_CREATED


# Put Tests
def test_unauthorized_put_url(db, api_client, fc_series, create_put_data):
    resp = api_client.put(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_put_url(api_client_with_credentials, fc_series, create_put_data):
    resp = api_client_with_credentials.put(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_staff_user_put_url(api_client_with_staff_credentials, fc_series, create_put_data):
    resp = api_client_with_staff_credentials.patch(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_200_OK


# Regular Tests
def test_view_url_accessible_by_name(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:series-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client):
    resp = api_client.get(reverse("api:series-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_valid_single_issue(api_client_with_credentials, fc_series, issue_with_arc):
    resp = api_client_with_credentials.get(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    # series = Series.objects.get(pk=fc_series.pk)
    # serializer = SeriesReadSerializer(series)
    # assert resp.data == serializer.data


def test_unauthorized_detail_view_url(api_client, fc_series):
    response = api_client.get(reverse("api:series-detail", kwargs={"pk": fc_series.pk}))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_series_search(api_client_with_credentials, bat_sups_series, fc_series):
    search_term = "batman superman"
    resp = api_client_with_credentials.get(f"/api/series/?name={quote_plus(search_term)}")
    expected = Series.objects.filter(
        reduce(operator.and_, (Q(name__icontains=q) for q in search_term.split()))
    ).annotate(num_issues=Count("issues", distinct=True))
    serializer = SeriesListSerializer(expected, many=True)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["results"] == serializer.data


def test_filter_by_creator_id(
    api_client_with_credentials,
    fc_series: Series,
    issue_with_arc,
    john_byrne: Creator,
    writer: Role,
):
    credit = Credits.objects.create(issue=issue_with_arc, creator=john_byrne)
    credit.role.add(writer)
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"creator_id": john_byrne.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == fc_series.id


def test_filter_by_creator_id_no_match(
    api_client_with_credentials, fc_series: Series, john_byrne: Creator
):
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"creator_id": john_byrne.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_filter_by_imprint_id(
    api_client_with_credentials, sandman_series: Series, vertigo_imprint: Imprint
):
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"imprint_id": vertigo_imprint.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == sandman_series.id


def test_filter_by_imprint_id_no_match(
    api_client_with_credentials, fc_series: Series, vertigo_imprint: Imprint
):
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"imprint_id": vertigo_imprint.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_filter_by_character_id(
    api_client_with_credentials, fc_series: Series, issue_with_arc, superman: Character
):
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"character_id": superman.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == fc_series.id


def test_filter_by_character_id_no_match(
    api_client_with_credentials, fc_series: Series, superman: Character
):
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"character_id": superman.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_filter_by_team_id(
    api_client_with_credentials, fc_series: Series, basic_issue, teen_titans: Team
):
    basic_issue.teams.add(teen_titans)
    resp = api_client_with_credentials.get(reverse("api:series-list"), {"team_id": teen_titans.id})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == fc_series.id


def test_filter_by_team_id_no_match(
    api_client_with_credentials, fc_series: Series, teen_titans: Team
):
    resp = api_client_with_credentials.get(reverse("api:series-list"), {"team_id": teen_titans.id})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_filter_by_universe_id(
    api_client_with_credentials, fc_series: Series, basic_issue, earth_2_universe: Universe
):
    basic_issue.universes.add(earth_2_universe)
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"universe_id": earth_2_universe.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == fc_series.id


def test_filter_by_universe_id_no_match(
    api_client_with_credentials, fc_series: Series, earth_2_universe: Universe
):
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"universe_id": earth_2_universe.id}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_filter_by_role_id(
    api_client_with_credentials,
    fc_series: Series,
    basic_issue,
    john_byrne: Creator,
    writer: Role,
):
    credit = Credits.objects.create(issue=basic_issue, creator=john_byrne)
    credit.role.add(writer)
    resp = api_client_with_credentials.get(reverse("api:series-list"), {"role_id": writer.id})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == fc_series.id


def test_filter_by_role_id_no_match(api_client_with_credentials, fc_series: Series, writer: Role):
    resp = api_client_with_credentials.get(reverse("api:series-list"), {"role_id": writer.id})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_filter_by_multiple_role_ids(
    api_client_with_credentials,
    fc_series: Series,
    basic_issue,
    john_byrne: Creator,
    writer: Role,
):
    penciller = Role.objects.create(name="Penciller", notes="", order=30)
    credit = Credits.objects.create(issue=basic_issue, creator=john_byrne)
    credit.role.add(writer, penciller)
    resp = api_client_with_credentials.get(
        reverse("api:series-list"), {"role_id": f"{writer.id},{penciller.id}"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == fc_series.id


def test_list_series_year_end_null(api_client_with_credentials, fc_series: Series):
    resp = api_client_with_credentials.get(reverse("api:series-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["results"][0]["year_end"] is None


def test_list_series_year_end_set(
    api_client_with_credentials, fc_series: Series, create_user, dc_comics, single_issue_type
):
    user = create_user()
    Series.objects.create(
        name="Completed Series",
        slug="completed-series",
        publisher=dc_comics,
        volume="1",
        year_began=2000,
        year_end=2005,
        series_type=single_issue_type,
        status=Series.Status.COMPLETED,
        edited_by=user,
        created_by=user,
    )
    resp = api_client_with_credentials.get(reverse("api:series-list"))
    assert resp.status_code == status.HTTP_200_OK
    completed = next(r for r in resp.data["results"] if r["year_end"] is not None)
    assert completed["year_end"] == 2005
