"""Tests for the shared active-filter chip builder and its per-list wrappers."""

from comicsdb.views.filter_chips import build_filter_chips, series_type_names
from comicsdb.views.series_list_helpers import build_active_filters as series_filters
from reading_lists.views import build_active_filters as reading_list_filters


def _chip(chips, label):
    return next(c for c in chips if c["label"] == label)


# ---------------------------------------------------------------------------
# build_filter_chips
# ---------------------------------------------------------------------------
def test_build_filter_chips_skips_page_and_empty_values(rf):
    request = rf.get("/", {"page": "2", "q": "", "name": "Batman"})
    chips = build_filter_chips(request, {"name": "Name"})
    assert [c["label"] for c in chips] == ["Name"]


def test_build_filter_chips_custom_skip(rf):
    request = rf.get("/", {"sort": "added", "q": "x"})
    assert build_filter_chips(request, {}, skip={"page", "sort"})[0]["label"] == "Q"
    assert len(build_filter_chips(request, {})) == 2


def test_build_filter_chips_display_map_with_raw_fallback(rf):
    request = rf.get("/", {"kind": "a", "other": "zz"})
    chips = build_filter_chips(request, {}, {"kind": {"a": "Alpha"}, "other": {"a": "Alpha"}})
    assert _chip(chips, "Kind")["value"] == "Alpha"
    assert _chip(chips, "Other")["value"] == "zz"


def test_build_filter_chips_remove_url_keeps_other_params_but_not_page(rf):
    request = rf.get("/", {"name": "Batman", "sort": "added", "page": "3"})
    chip = _chip(build_filter_chips(request, {"name": "Name"}, skip={"page", "sort"}), "Name")
    assert chip["remove_url"] == "?sort=added"


def test_build_filter_chips_remove_url_for_last_param(rf):
    chip = build_filter_chips(rf.get("/", {"name": "Batman"}), {})[0]
    assert chip["remove_url"] == "?"


def test_series_type_names_prefers_supplied_map(rf):
    assert series_type_names(rf.get("/", {"series_type": "1"}), {"1": "Given"}) == {"1": "Given"}


def test_series_type_names_skips_query_without_filter(rf):
    # No db fixture: any query here would raise.
    assert series_type_names(rf.get("/")) == {}


def test_series_type_names_queries_when_filter_active(rf, single_issue_type):
    names = series_type_names(rf.get("/", {"series_type": str(single_issue_type.pk)}))
    assert names[str(single_issue_type.pk)] == single_issue_type.name


# ---------------------------------------------------------------------------
# Series list wrapper
# ---------------------------------------------------------------------------
def test_series_filters_resolve_status_language_and_type(rf):
    request = rf.get("/", {"status": "2", "language": "it", "series_type": "7", "page": "2"})
    chips = series_filters(request, type_names={"7": "Omnibus"})
    assert _chip(chips, "Status")["value"] == "Completed"
    assert _chip(chips, "Language")["value"] == "Italian"
    assert _chip(chips, "Type")["value"] == "Omnibus"
    assert len(chips) == 3


def test_series_filters_include_sort_as_a_chip(rf):
    """Unlike the issue list, the series list doesn't skip ``sort`` (it has no sort control)."""
    chips = series_filters(rf.get("/", {"sort": "x"}), type_names={})
    assert [c["label"] for c in chips] == ["Sort"]


# ---------------------------------------------------------------------------
# Reading list wrapper
# ---------------------------------------------------------------------------
def test_reading_list_filters_resolve_choices(rf):
    request = rf.get(
        "/",
        {
            "list_type": "EVENT",
            "attribution_source": "CBRO",
            "average_rating__gte": "4",
            "is_private": "true",
        },
    )
    chips = reading_list_filters(request)
    assert _chip(chips, "List Type")["value"] == "Event"
    assert _chip(chips, "Attribution")["value"] == "Comic Book Reading Orders"
    assert _chip(chips, "Min Rating")["value"] == "4+ Stars"
    assert _chip(chips, "Privacy")["value"] == "Private"


def test_reading_list_filters_unknown_choice_shown_raw(rf):
    chips = reading_list_filters(rf.get("/", {"list_type": "NOPE"}))
    assert _chip(chips, "List Type")["value"] == "NOPE"
