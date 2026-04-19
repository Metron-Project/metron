from datetime import date
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from djmoney.money import Money
from rest_framework import status

from comicsdb.models import Issue
from comicsdb.models.arc import Arc
from comicsdb.models.series import Series
from comicsdb.models.universe import Universe


@pytest.fixture
def create_issue_data(fc_series: Series, fc_arc: Arc, earth_2_universe: Universe):
    return {
        "series": fc_series.id,
        "name": ["This Man, This Monster"],
        "number": "1",
        "cover_date": date(2023, 1, 1),
        "store_date": date(2023, 1, 15),
        "price": Decimal("3.99"),
        "sku": "1022DC019",
        "upc": "76194137738400111",
        "page": 32,
        "arcs": [fc_arc.id],
        "universes": [earth_2_universe.id],
    }


@pytest.fixture
def create_put_data(earth_2_universe: Universe):
    return {
        "name": ["This Man, This Monster", "Blah, Blah"],
        "universes": [earth_2_universe.id],
    }


# Post Tests
def test_unauthorized_post_url(db, api_client, create_issue_data):
    resp = api_client.post(reverse("api:issue-list"), data=create_issue_data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_post_url(api_client_with_credentials, create_issue_data):
    resp = api_client_with_credentials.post(reverse("api:issue-list"), data=create_issue_data)
    assert resp.status_code == status.HTTP_403_FORBIDDEN


# TODO: Fix Customuser foreign-key IntegrityError when *all* test are ran.
# def test_staff_user_post_url(db, api_client_with_staff_credentials, create_issue_data):
#     resp = api_client_with_staff_credentials.post(
#         reverse("api:issue-list"), data=create_issue_data
#     )
#     assert resp.status_code == status.HTTP_201_CREATED


# Put Tests
def test_unauthorized_put_url(db, api_client, issue_with_arc, create_put_data):
    resp = api_client.put(
        reverse("api:issue-detail", kwargs={"pk": issue_with_arc.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_user_put_url(api_client_with_credentials, issue_with_arc, create_put_data):
    resp = api_client_with_credentials.put(
        reverse("api:issue-detail", kwargs={"pk": issue_with_arc.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_staff_user_put_url(api_client_with_staff_credentials, issue_with_arc, create_put_data):
    resp = api_client_with_staff_credentials.patch(
        reverse("api:issue-detail", kwargs={"pk": issue_with_arc.pk}), data=create_put_data
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data.get("universes") == create_put_data.get("universes")


# Regular Tests
def test_view_url_accessible_by_name(api_client_with_credentials, list_of_issues):
    resp = api_client_with_credentials.get(reverse("api:issue-list"))
    assert resp.status_code == status.HTTP_200_OK


def test_unauthorized_view_url(api_client, list_of_issues):
    resp = api_client.get(reverse("api:issue-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_valid_single_arc(api_client_with_credentials, issue_with_arc):
    resp = api_client_with_credentials.get(
        reverse("api:issue-detail", kwargs={"pk": issue_with_arc.pk})
    )
    assert resp.status_code == status.HTTP_200_OK


def test_get_invalid_single_arc(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:issue-detail", kwargs={"pk": "10"}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_unauthorized_detail_view_url(api_client, issue_with_arc):
    resp = api_client.get(reverse("api:issue-detail", kwargs={"pk": issue_with_arc.pk}))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestIssuePriceField:
    @pytest.fixture
    def usd_issue(self, create_user, fc_series):
        user = create_user()
        return Issue.objects.create(
            series=fc_series,
            number="10",
            slug="final-crisis-10",
            cover_date=timezone.now().date(),
            price=Money(Decimal("3.99"), "USD"),
            edited_by=user,
            created_by=user,
        )

    @pytest.fixture
    def gbp_issue(self, create_user, fc_series):
        user = create_user()
        return Issue.objects.create(
            series=fc_series,
            number="11",
            slug="final-crisis-11",
            cover_date=timezone.now().date(),
            price=Money(Decimal("3.99"), "GBP"),
            edited_by=user,
            created_by=user,
        )

    @pytest.fixture
    def base_issue_data(self, fc_series):
        return {
            "series": fc_series.id,
            "number": "99",
            "cover_date": date(2024, 1, 1),
        }

    # Retrieve tests

    def test_retrieve_usd_price_amount(self, api_client_with_credentials, usd_issue):
        resp = api_client_with_credentials.get(
            reverse("api:issue-detail", kwargs={"pk": usd_issue.pk})
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["price"] == "3.99"

    def test_retrieve_usd_price_currency(self, api_client_with_credentials, usd_issue):
        resp = api_client_with_credentials.get(
            reverse("api:issue-detail", kwargs={"pk": usd_issue.pk})
        )
        assert resp.data["price_currency"] == "USD"

    def test_retrieve_gbp_price_amount(self, api_client_with_credentials, gbp_issue):
        resp = api_client_with_credentials.get(
            reverse("api:issue-detail", kwargs={"pk": gbp_issue.pk})
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["price"] == "3.99"

    def test_retrieve_gbp_price_currency(self, api_client_with_credentials, gbp_issue):
        resp = api_client_with_credentials.get(
            reverse("api:issue-detail", kwargs={"pk": gbp_issue.pk})
        )
        assert resp.data["price_currency"] == "GBP"

    # Patch tests

    def test_patch_usd_string_price(self, api_client_with_staff_credentials, usd_issue):
        url = reverse("api:issue-detail", kwargs={"pk": usd_issue.pk})
        resp = api_client_with_staff_credentials.patch(url, data={"price": "4.99"})
        assert resp.status_code == status.HTTP_200_OK
        detail = api_client_with_staff_credentials.get(url)
        assert detail.data["price"] == "4.99"
        assert detail.data["price_currency"] == "USD"

    def test_patch_gbp_dict_price(self, api_client_with_staff_credentials, usd_issue):
        url = reverse("api:issue-detail", kwargs={"pk": usd_issue.pk})
        resp = api_client_with_staff_credentials.patch(
            url,
            data={"price": {"amount": 3.99, "currency": "GBP"}},
            format="json",
        )
        assert resp.status_code == status.HTTP_200_OK
        detail = api_client_with_staff_credentials.get(url)
        assert detail.data["price"] == "3.99"
        assert detail.data["price_currency"] == "GBP"

    def test_patch_invalid_currency_returns_400(self, api_client_with_staff_credentials, usd_issue):
        resp = api_client_with_staff_credentials.patch(
            reverse("api:issue-detail", kwargs={"pk": usd_issue.pk}),
            data={"price": {"amount": 3.99, "currency": "EUR"}},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # Post tests

    def test_post_usd_string_price(self, api_client_with_staff_credentials, base_issue_data):
        base_issue_data["price"] = "3.99"
        resp = api_client_with_staff_credentials.post(
            reverse("api:issue-list"), data=base_issue_data
        )
        assert resp.status_code == status.HTTP_201_CREATED
        detail = api_client_with_staff_credentials.get(
            reverse("api:issue-detail", kwargs={"pk": resp.data["id"]})
        )
        assert detail.data["price"] == "3.99"
        assert detail.data["price_currency"] == "USD"

    def test_post_gbp_dict_price(self, api_client_with_staff_credentials, base_issue_data):
        base_issue_data["price"] = {"amount": 3.99, "currency": "GBP"}
        resp = api_client_with_staff_credentials.post(
            reverse("api:issue-list"), data=base_issue_data, format="json"
        )
        assert resp.status_code == status.HTTP_201_CREATED
        detail = api_client_with_staff_credentials.get(
            reverse("api:issue-detail", kwargs={"pk": resp.data["id"]})
        )
        assert detail.data["price"] == "3.99"
        assert detail.data["price_currency"] == "GBP"

    def test_post_invalid_currency_returns_400(
        self, api_client_with_staff_credentials, base_issue_data
    ):
        base_issue_data["price"] = {"amount": 3.99, "currency": "EUR"}
        resp = api_client_with_staff_credentials.post(
            reverse("api:issue-list"), data=base_issue_data, format="json"
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
