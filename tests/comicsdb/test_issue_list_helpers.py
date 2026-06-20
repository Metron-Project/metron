from unittest.mock import MagicMock

import pytest
from django.test import RequestFactory

from comicsdb.models.series import SeriesType
from comicsdb.views.issue_list_helpers import (
    SORT_OPTIONS,
    apply_sort,
    build_active_filters,
)


@pytest.fixture
def rf():
    return RequestFactory()


# ---------------------------------------------------------------------------
# apply_sort
# ---------------------------------------------------------------------------


def test_apply_sort_default_uses_model_ordering(rf):
    qs = MagicMock()
    request = rf.get("/")
    result = apply_sort(qs, request)
    qs.order_by.assert_called_once_with(*SORT_OPTIONS[""]["order"])
    assert result == qs.order_by.return_value


def test_apply_sort_cover_new(rf):
    qs = MagicMock()
    request = rf.get("/", {"sort": "cover_new"})
    apply_sort(qs, request)
    qs.order_by.assert_called_once_with(*SORT_OPTIONS["cover_new"]["order"])


def test_apply_sort_cover_old(rf):
    qs = MagicMock()
    request = rf.get("/", {"sort": "cover_old"})
    apply_sort(qs, request)
    qs.order_by.assert_called_once_with(*SORT_OPTIONS["cover_old"]["order"])


def test_apply_sort_added(rf):
    qs = MagicMock()
    request = rf.get("/", {"sort": "added"})
    apply_sort(qs, request)
    qs.order_by.assert_called_once_with(*SORT_OPTIONS["added"]["order"])


def test_apply_sort_unknown_value_returns_queryset_unchanged(rf):
    qs = MagicMock()
    request = rf.get("/", {"sort": "garbage_value"})
    result = apply_sort(qs, request)
    qs.order_by.assert_not_called()
    assert result is qs


# ---------------------------------------------------------------------------
# build_active_filters — no DB required
# ---------------------------------------------------------------------------


def test_build_active_filters_empty_returns_no_chips(rf):
    request = rf.get("/")
    assert build_active_filters(request) == []


def test_build_active_filters_page_and_sort_are_excluded(rf):
    request = rf.get("/", {"page": "2", "sort": "cover_new"})
    assert build_active_filters(request) == []


def test_build_active_filters_search_chip(rf):
    request = rf.get("/", {"q": "batman"})
    chips = build_active_filters(request)
    assert len(chips) == 1
    assert chips[0]["label"] == "Search"
    assert chips[0]["value"] == "batman"
    assert chips[0]["remove_url"] == "?"


def test_build_active_filters_remove_url_preserves_other_params(rf):
    request = rf.get("/", {"q": "batman", "cover_year": "2020"})
    chips = build_active_filters(request)
    assert len(chips) == 2
    search_chip = next(c for c in chips if c["label"] == "Search")
    assert "cover_year=2020" in search_chip["remove_url"]
    assert "q=" not in search_chip["remove_url"]


def test_build_active_filters_page_dropped_from_remove_url(rf):
    request = rf.get("/", {"q": "batman", "page": "3"})
    chips = build_active_filters(request)
    assert len(chips) == 1
    assert "page" not in chips[0]["remove_url"]


def test_build_active_filters_cover_month_resolved_to_name(rf):
    request = rf.get("/", {"cover_month": "4"})
    chips = build_active_filters(request)
    assert chips[0]["value"] == "April"


def test_build_active_filters_cover_month_unknown_falls_back_to_raw(rf):
    request = rf.get("/", {"cover_month": "99"})
    chips = build_active_filters(request)
    assert chips[0]["value"] == "99"


def test_build_active_filters_series_type_resolved_from_supplied_dict(rf):
    request = rf.get("/", {"series_type": "3"})
    type_names = {"3": "Ongoing Series"}
    chips = build_active_filters(request, type_names=type_names)
    assert chips[0]["label"] == "Type"
    assert chips[0]["value"] == "Ongoing Series"


def test_build_active_filters_series_type_falls_back_to_id_when_not_in_dict(rf):
    request = rf.get("/", {"series_type": "99"})
    type_names = {"3": "Ongoing Series"}
    chips = build_active_filters(request, type_names=type_names)
    assert chips[0]["value"] == "99"


def test_build_active_filters_unknown_param_uses_title_case_label(rf):
    request = rf.get("/", {"some_custom_param": "foo"})
    chips = build_active_filters(request)
    assert chips[0]["label"] == "Some Custom Param"


@pytest.mark.django_db
def test_build_active_filters_fetches_series_type_from_db_when_not_supplied(rf):
    st = SeriesType.objects.first()
    if st is None:
        pytest.skip("No SeriesType rows in DB")
    request = rf.get("/", {"series_type": str(st.id)})
    chips = build_active_filters(request)
    assert chips[0]["value"] == st.name
