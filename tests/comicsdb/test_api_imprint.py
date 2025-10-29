import pytest
from django.urls import reverse
from rest_framework import status


@pytest.fixture
def create_put_data(dc_comics) -> dict[str, str | int]:
    return {
        "name": "Vertigo",
        "publisher": dc_comics.id,
        "founded": 1989,
        "desc": "Blah blah blah",
    }


def test_unauthorized_post_url(db, api_client, create_put_data):
    resp = api_client.post(reverse("api:imprint-list"), data=create_put_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_put_data):
    resp = api_client_with_credentials.post(reverse("api:imprint-list"), data=create_put_data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_group_user_post_url(db, api_client_with_staff_credentials, create_put_data):
    resp = api_client_with_staff_credentials.post(reverse("api:imprint-list"), data=create_put_data)
    assert resp.status_code == status.HTTP_201_CREATED
    # TODO: Fix test to compare data. Specifically the KeyError: 'request' for the
    #       get_resource_url()
    # new_pub = Publisher.objects.get(name=create_publisher_data["name"])
    # serializer = PublisherSerializer(new_pub)
    # assert resp.data == serializer.data


# Regular Tests
def test_view_url_accessible_by_name(
    api_client_with_credentials, vertigo_imprint, black_label_imprint
):
    resp = api_client_with_credentials.get(reverse("api:imprint-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client, vertigo_imprint, black_label_imprint):
    resp = api_client.get(reverse("api:imprint-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_valid_single_imprint(api_client_with_credentials, vertigo_imprint):
    response = api_client_with_credentials.get(
        reverse("api:imprint-detail", kwargs={"pk": vertigo_imprint.pk})
    )
    assert response.status_code == status.HTTP_200_OK
    # TODO: Fix test to compare data. Specifically the KeyError: 'request' for
    #       the get_resource_url()
    # publisher = Publisher.objects.get(pk=dc_comics.pk)
    # serializer = PublisherSerializer(publisher)
    # assert response.data == serializer.data


def test_get_invalid_single_imprint(api_client_with_credentials):
    response = api_client_with_credentials.get(reverse("api:imprint-detail", kwargs={"pk": "10"}))
    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_unauthorized_detail_view_url(api_client, vertigo_imprint):
    response = api_client.get(reverse("api:imprint-detail", kwargs={"pk": vertigo_imprint.pk}))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# def test_publisher_series_list_view(api_client_with_credentials, dc_comics, fc_series):
#     resp = api_client_with_credentials.get(
#         reverse("api:publisher-series-list", kwargs={"pk": dc_comics.pk})
#     )
#     serializer = SeriesListSerializer(fc_series)
#     assert resp.data["count"] == 1
#     assert resp.data["next"] is None
#     assert resp.data["previous"] is None
#     assert resp.data["results"][0] == serializer.data
#     assert resp.status_code == status.HTTP_200_OK
