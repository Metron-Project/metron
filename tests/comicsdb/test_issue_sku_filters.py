"""Exact SKU searches include variant covers in both the API and website."""

import pytest
from django.urls import reverse

from comicsdb.models import Issue, Variant

MAIN_SKU = "1022DC019"
VARIANT_SKU = "1022DC020"
OTHER_SKU = "1022DC021"


@pytest.fixture(params=["api", "website"])
def sku_search(request, api_client_with_credentials, auto_login_user):
    if request.param == "website":
        client, _ = auto_login_user()
        url = reverse("issue:list")
    else:
        client = api_client_with_credentials
        url = reverse("api:issue-list")

    def search(value, **filters):
        response = client.get(url, {"sku": value, **filters})
        assert response.status_code == 200
        if request.param == "website":
            return [issue.pk for issue in response.context["issue_list"]]
        data = response.json()
        ids = [row["id"] for row in data["results"]]
        assert data["count"] == len(ids)
        return ids

    return search


@pytest.mark.parametrize(
    ("main_sku", "variant_skus", "query", "matches"),
    [
        (MAIN_SKU, [], MAIN_SKU, True),
        (MAIN_SKU, [VARIANT_SKU, OTHER_SKU], MAIN_SKU, True),
        (MAIN_SKU, [VARIANT_SKU], VARIANT_SKU, True),
        ("", [VARIANT_SKU], VARIANT_SKU, True),
        ("", [VARIANT_SKU, VARIANT_SKU], VARIANT_SKU, True),
        (VARIANT_SKU, [VARIANT_SKU], VARIANT_SKU, True),
        (MAIN_SKU, [VARIANT_SKU], OTHER_SKU, False),
        (MAIN_SKU, [VARIANT_SKU], "", True),
        (MAIN_SKU, [VARIANT_SKU], VARIANT_SKU.lower(), True),
        (MAIN_SKU, [VARIANT_SKU], "1022DC", False),
        (MAIN_SKU, [VARIANT_SKU], "DC020", False),
        (MAIN_SKU, [], MAIN_SKU.lower(), True),
    ],
    ids=[
        "main_only",
        "main_with_variants",
        "variant_only",
        "blank_main",
        "duplicate_variants",
        "main_and_variant",
        "no_match",
        "empty_query",
        "variant_case_insensitive",
        "no_prefix_match",
        "no_substring_match",
        "main_case_insensitive",
    ],
)
def test_exact_sku_matching(sku_search, basic_issue, main_sku, variant_skus, query, matches):
    basic_issue.sku = main_sku
    basic_issue.save()
    for index, sku in enumerate(variant_skus):
        Variant.objects.create(issue=basic_issue, name=f"Variant {index}", sku=sku)
    assert sku_search(query) == ([basic_issue.pk] if matches else [])


def test_variant_sku_respects_other_filters(sku_search, basic_issue):
    Variant.objects.create(issue=basic_issue, name="B", sku=VARIANT_SKU)
    assert sku_search(VARIANT_SKU, number=basic_issue.number) == [basic_issue.pk]
    assert sku_search(VARIANT_SKU, number="999") == []


def test_sku_keeps_distinct_matching_issues(sku_search, basic_issue):
    basic_issue.sku = MAIN_SKU
    basic_issue.save()
    second = Issue.objects.create(
        series=basic_issue.series,
        number="2",
        cover_date=basic_issue.cover_date,
        created_by=basic_issue.created_by,
        edited_by=basic_issue.edited_by,
    )
    Variant.objects.create(issue=second, name="B", sku=MAIN_SKU)
    assert set(sku_search(MAIN_SKU)) == {basic_issue.pk, second.pk}


def test_sku_and_upc_filters_can_match_different_covers(sku_search, basic_issue):
    Variant.objects.create(issue=basic_issue, name="B", sku=VARIANT_SKU)
    Variant.objects.create(issue=basic_issue, name="C", upc="76194137738400121")
    assert sku_search(VARIANT_SKU, upc="76194137738400121") == [basic_issue.pk]
    assert sku_search(VARIANT_SKU, upc="75960609558200111") == []
