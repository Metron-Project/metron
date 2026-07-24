"""Shared helpers for series list views: active-filter chips.

Mirrors the structure of issue_list_helpers but covers the series filter
params exposed by SeriesViewFilter.
"""

from urllib.parse import urlencode

from comicsdb.models import Series, SeriesType

_NON_FILTER_PARAMS = {"page"}

FILTER_LABELS = {
    "q": "Search",
    "name": "Name",
    "alt_names": "Alternative Name",
    "series_type": "Type",
    "publisher_name": "Publisher",
    "publisher_id": "Publisher ID",
    "imprint_name": "Imprint",
    "imprint_id": "Imprint ID",
    "year_began": "Year Began",
    "year_began_gte": "Year Began (from)",
    "year_began_lte": "Year Began (to)",
    "year_end": "Year Ended",
    "status": "Status",
    "volume": "Volume",
}

_STATUS_LABELS = {str(k): v for k, v in Series.Status.choices}


def build_active_filters(request, type_names=None):
    """Build a list of ``{label, value, remove_url}`` dicts for the chip bar.

    ``remove_url`` drops that one param (and resets ``page``) while preserving
    every other active filter.

    Pass ``type_names`` (a ``{str(id): name}`` dict) to avoid a second DB hit
    when the caller has already fetched SeriesType rows for the filter form.
    """
    get = request.GET
    if type_names is None and get.get("series_type"):
        type_names = {str(t["id"]): t["name"] for t in SeriesType.objects.values("id", "name")}
    if type_names is None:
        type_names = {}

    chips = []
    for key in get:
        if key in _NON_FILTER_PARAMS:
            continue
        value = get.get(key)
        if not value:
            continue

        display = value
        if key == "series_type":
            display = type_names.get(value, value)
        elif key == "status":
            display = _STATUS_LABELS.get(value, value)

        kept = [(k, v) for k, v in get.items() if k not in (key, "page")]
        remove_url = f"?{urlencode(kept)}" if kept else "?"

        chips.append(
            {
                "label": FILTER_LABELS.get(key, key.replace("_", " ").title()),
                "value": display,
                "remove_url": remove_url,
            }
        )
    return chips
