"""Shared helpers for issue list views: result sorting, active-filter chips and
issue-number range filtering.

Kept in its own module so the four issue list views
(IssueList, WeekList, NextWeekList, FutureList) can share one definition and the
diff to ``views/issue.py`` stays small. No new dependencies.
"""

from django.utils.translation import gettext_lazy as _

from comicsdb.views.filter_chips import build_filter_chips, series_type_names

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
    "desc_is_solicitation": _("Solicitation"),
}

# Boolean filter params, whose ``true``/``false`` values render as Yes/No.
_BOOLEAN_PARAMS = {"desc_is_solicitation"}
_BOOLEAN_DISPLAY = {"true": _("Yes"), "false": _("No")}

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
    """Build the issue list's filter chips (see ``build_filter_chips``).

    Pass ``type_names`` (a ``{str(id): name}`` dict) to avoid a second DB hit
    when the caller has already fetched SeriesType rows for the filter form.
    """
    display_maps = {
        "series_type": series_type_names(request, type_names),
        "cover_month": _MONTHS,
        **dict.fromkeys(_BOOLEAN_PARAMS, _BOOLEAN_DISPLAY),
    }
    return build_filter_chips(request, FILTER_LABELS, display_maps, skip=_NON_FILTER_PARAMS)


# ---------------------------------------------------------------------------
# Issue-number ranges
# ---------------------------------------------------------------------------
def filter_issues_by_number_range(issues, start_number, end_number):
    """Restrict an ordered iterable of issues to the inclusive range of issue numbers.

    Either bound may be omitted to mean "from the beginning" / "through the end".
    Matching is by ``Issue.number`` string equality, in the given iteration order.
    """
    if not start_number and not end_number:
        return list(issues)

    filtered = []
    in_range = not start_number
    for issue in issues:
        if start_number and issue.number == start_number:
            in_range = True
        if in_range:
            filtered.append(issue)
        if end_number and issue.number == end_number:
            break
    return filtered
