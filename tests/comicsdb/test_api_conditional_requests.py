from django.urls import reverse
from rest_framework import status


def test_arc_returns_last_modified_header(api_client_with_credentials, wwh_arc):
    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "Last-Modified" in resp


def test_arc_conditional_request_returns_304(api_client_with_credentials, wwh_arc):
    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_character_conditional_request_returns_304(api_client_with_credentials, superman):
    resp = api_client_with_credentials.get(
        reverse("api:character-detail", kwargs={"pk": superman.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:character-detail", kwargs={"pk": superman.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_creator_conditional_request_returns_304(api_client_with_credentials, john_byrne):
    resp = api_client_with_credentials.get(
        reverse("api:creator-detail", kwargs={"pk": john_byrne.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:creator-detail", kwargs={"pk": john_byrne.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_issue_conditional_request_returns_304(api_client_with_credentials, basic_issue):
    resp = api_client_with_credentials.get(
        reverse("api:issue-detail", kwargs={"pk": basic_issue.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:issue-detail", kwargs={"pk": basic_issue.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_publisher_conditional_request_returns_304(api_client_with_credentials, dc_comics):
    resp = api_client_with_credentials.get(
        reverse("api:publisher-detail", kwargs={"pk": dc_comics.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:publisher-detail", kwargs={"pk": dc_comics.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_series_conditional_request_returns_304(api_client_with_credentials, fc_series):
    resp = api_client_with_credentials.get(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:series-detail", kwargs={"pk": fc_series.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_team_conditional_request_returns_304(api_client_with_credentials, teen_titans):
    resp = api_client_with_credentials.get(
        reverse("api:team-detail", kwargs={"pk": teen_titans.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:team-detail", kwargs={"pk": teen_titans.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_universe_conditional_request_returns_304(
    api_client_with_credentials, earth_2_universe
):
    resp = api_client_with_credentials.get(
        reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:universe-detail", kwargs={"pk": earth_2_universe.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_imprint_conditional_request_returns_304(
    api_client_with_credentials, vertigo_imprint
):
    resp = api_client_with_credentials.get(
        reverse("api:imprint-detail", kwargs={"pk": vertigo_imprint.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    last_modified = resp["Last-Modified"]

    resp = api_client_with_credentials.get(
        reverse("api:imprint-detail", kwargs={"pk": vertigo_imprint.pk}),
        HTTP_IF_MODIFIED_SINCE=last_modified,
    )
    assert resp.status_code == status.HTTP_304_NOT_MODIFIED


def test_conditional_request_with_old_date_returns_200(
    api_client_with_credentials, wwh_arc
):
    resp = api_client_with_credentials.get(
        reverse("api:arc-detail", kwargs={"pk": wwh_arc.pk}),
        HTTP_IF_MODIFIED_SINCE="Wed, 01 Jan 2020 00:00:00 GMT",
    )
    assert resp.status_code == status.HTTP_200_OK


def test_list_endpoint_does_not_return_304(api_client_with_credentials, wwh_arc, fc_arc):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "Last-Modified" not in resp
