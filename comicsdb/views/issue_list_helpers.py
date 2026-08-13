"""Shared helpers for issue list views: result sorting + active-filter chips.

Kept in its own module so the four issue list views
(IssueList, WeekList, NextWeekList, FutureList) can share one definition and the
diff to ``views/issue.py`` stays small. No new dependencies.
"""

from urllib.parse import urlencode

from django.utils.translation import gettext_lazy as _

from comicsdb.models.series import SeriesType

# ---------------------------------------------------------------------------
# Sorting
# ---------------------------------------------------------------------------
# Whitelisted sort options. The GET param ``?sort=`` is validated against these
# keys, so an arbitrary/garbage value can never reach ``order_by`` — it simply
# falls back to the model default. The empty key "" is the default (model Meta
# ordering) and renders first / selected when no sort is chosen.
SORT_OPTIONS = {
    "": {
        "label": _("Series A\u2013Z"),
        "order": ["series__sort_name", "cover_date", "store_date", "number"],
    },
    "cover_new": {
        "label": _("Cover date (newest)"),
        "order": ["-cover_date", "series__sort_name", "number"],
    },
    "cover_old": {
        "label": _("Cover date (oldest)"),
        "order": ["cover_date", "series__sort_name", "number"],
    },
    "added": {
        "label": _("Recently added"),
        "order": ["-created_on", "series__sort_name", "number"],
    },
}


def apply_sort(queryset, request):
    """Return ``queryset`` ordered per a whitelisted ``?sort=`` param.

    Unknown/empty values leave the queryset on its model-default ordering.
    """
    option = SORT_OPTIONS.get(request.GET.get("sort", ""))
    return queryset.order_by(*option["order"]) if option else queryset


# ---------------------------------------------------------------------------
# Active-filter chips
# ---------------------------------------------------------------------------
# GET params that are NOT user-facing filters (so they don't render as chips).
_NON_FILTER_PARAMS = {"page", "sort"}

# Human-readable labels for each filter param the issue browse exposes.
FILTER_LABELS = {
    "q": _("Search"),
    "series_name": _("Series"),
    "series_type": _("Type"),
    "series_volume": _("Volume"),
    "publisher_name": _("Publisher"),
    "number": _("Number"),
    "alt_number": _("Alt number"),
    "cover_year": _("Cover year"),
    "cover_month": _("Cover month"),
    "store_date_after": _("Store date from"),
    "store_date_before": _("Store date to"),
    "foc_date_after": _("FOC date from"),
    "foc_date_before": _("FOC date to"),
    "upc": _("UPC"),
    "sku": _("SKU"),
    "cv_id": _("Comic Vine ID"),
    "gcd_id": _("GCD ID"),
}

_MONTHS = {
    "1": _("January"),
    "2": _("February"),
    "3": _("March"),
    "4": _("April"),
    "5": _("May"),
    "6": _("June"),
    "7": _("July"),
    "8": _("August"),
    "9": _("September"),
    "10": _("October"),
    "11": _("November"),
    "12": _("December"),
}


def build_active_filters(request, type_names=None):
    """Build a list of ``{label, value, remove_url}`` dicts for the chip bar.

    ``remove_url`` drops that one param (and resets ``page``) while preserving
    every other active filter and the current sort.

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
        elif key == "cover_month":
            display = _MONTHS.get(value, value)

        # Every current param except the one being removed and the page cursor.
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
