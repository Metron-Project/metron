"""UPC lookups return parent issues for main and variant covers without duplicates."""

import pytest
from django.urls import reverse

from comicsdb.models import Issue, Variant

MAIN_UPC = "76194137738400111"
VARIANT_UPC = "76194137738400121"
OTHER_UPC = "75960609558200111"


@pytest.fixture(params=["api_exact", "api_prefix", "website_exact"])
def upc_search(request, api_client_with_credentials, auto_login_user):
    """Exercise both API filters and the website's exact filter via real requests."""
    if request.param == "website_exact":
        client, _ = auto_login_user()
        url = reverse("issue:list")
    else:
        client = api_client_with_credentials
        url = reverse("api:issue-list")
    prefix = request.param == "api_prefix"
    field = "upc_starts_with" if prefix else "upc"

    def search(value, **filters):
        value = value[:12] if prefix else value
        response = client.get(url, {field: value, **filters})
        assert response.status_code == 200
        if request.param == "website_exact":
            return [issue.pk for issue in response.context["issue_list"]]
        data = response.json()
        ids = [row["id"] for row in data["results"]]
        assert data["count"] == len(ids)
        return ids

    return search


def test_upc_main_cover_without_variants(upc_search, basic_issue):
    basic_issue.upc = MAIN_UPC
    basic_issue.save()
    assert upc_search(MAIN_UPC) == [basic_issue.pk]


def test_upc_main_cover_with_multiple_variants_is_unique(upc_search, basic_issue):
    basic_issue.upc = MAIN_UPC
    basic_issue.save()
    Variant.objects.create(issue=basic_issue, name="B", upc=VARIANT_UPC)
    Variant.objects.create(issue=basic_issue, name="C", upc=OTHER_UPC)
    assert upc_search(MAIN_UPC) == [basic_issue.pk]


@pytest.mark.parametrize("main_upc", [OTHER_UPC, ""])
def test_upc_variant_cover_only(upc_search, basic_issue, main_upc):
    basic_issue.upc = main_upc
    basic_issue.save()
    Variant.objects.create(issue=basic_issue, name="B", upc=VARIANT_UPC)
    assert upc_search(VARIANT_UPC) == [basic_issue.pk]


def test_upc_multiple_matching_variants_are_unique(upc_search, basic_issue):
    Variant.objects.create(issue=basic_issue, name="B", upc=VARIANT_UPC)
    Variant.objects.create(issue=basic_issue, name="C", upc=VARIANT_UPC)
    assert upc_search(VARIANT_UPC) == [basic_issue.pk]


def test_upc_main_and_variant_matching_are_unique(upc_search, basic_issue):
    basic_issue.upc = VARIANT_UPC
    basic_issue.save()
    Variant.objects.create(issue=basic_issue, name="B", upc=VARIANT_UPC)
    assert upc_search(VARIANT_UPC) == [basic_issue.pk]


def test_upc_no_matching_cover(upc_search, basic_issue):
    basic_issue.upc = MAIN_UPC
    basic_issue.save()
    Variant.objects.create(issue=basic_issue, name="B", upc=VARIANT_UPC)
    assert upc_search(OTHER_UPC) == []


def test_upc_empty_does_not_filter(upc_search, basic_issue):
    assert upc_search("") == [basic_issue.pk]


def test_upc_variant_match_respects_other_filters(upc_search, basic_issue):
    Variant.objects.create(issue=basic_issue, name="B", upc=VARIANT_UPC)
    assert upc_search(VARIANT_UPC, number=basic_issue.number) == [basic_issue.pk]
    assert upc_search(VARIANT_UPC, number="999") == []


def test_upc_keeps_distinct_matching_issues(upc_search, basic_issue):
    basic_issue.upc = MAIN_UPC
    basic_issue.save()
    second = Issue.objects.create(
        series=basic_issue.series,
        number="2",
        cover_date=basic_issue.cover_date,
        created_by=basic_issue.created_by,
        edited_by=basic_issue.edited_by,
    )
    Variant.objects.create(issue=second, name="B", upc=MAIN_UPC)
    assert set(upc_search(MAIN_UPC)) == {basic_issue.pk, second.pk}
