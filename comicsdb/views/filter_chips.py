"""Active-filter chips shown above filtered list views.

Each list view (issues, series, reading lists) supplies its own labels and
value-to-display mappings; the chip-building logic lives here once.
"""

from urllib.parse import urlencode

from comicsdb.models.series import SeriesType


def build_filter_chips(request, labels, display_maps=None, skip=frozenset({"page"})):
    """Build a list of ``{label, value, remove_url}`` dicts for the chip bar.

    Args:
        request: The current request; every non-empty GET param not in ``skip``
            becomes a chip.
        labels: ``{param: label}``. Params without a label get a title-cased name.
        display_maps: ``{param: {raw value: display value}}`` for params whose
            raw value isn't human-readable (ids, choice keys, booleans). Values
            missing from a map are shown raw.
        skip: GET params that aren't user-facing filters (paging, sorting).

    ``remove_url`` drops that one param (and resets ``page``) while preserving
    every other param, including the current sort.
    """
    get = request.GET
    display_maps = display_maps or {}

    chips = []
    for key in get:
        if key in skip:
            continue
        value = get.get(key)
        if not value:
            continue

        # Every current param except the one being removed and the page cursor.
        kept = [(k, v) for k, v in get.items() if k not in (key, "page")]
        chips.append(
            {
                "label": labels.get(key, key.replace("_", " ").title()),
                "value": display_maps.get(key, {}).get(value, value),
                "remove_url": f"?{urlencode(kept)}" if kept else "?",
            }
        )
    return chips


def series_type_names(request, type_names=None):
    """Return a ``{str(id): name}`` map for a ``series_type`` chip.

    Uses ``type_names`` when the caller already fetched SeriesType rows for its
    filter form, and only queries when a ``series_type`` filter is active.
    """
    if type_names is not None:
        return type_names
    if request.GET.get("series_type"):
        return {str(t["id"]): t["name"] for t in SeriesType.objects.values("id", "name")}
    return {}
