"""Active-filter chips for the series list (the params exposed by SeriesViewFilter)."""

from django.conf import global_settings
from django.utils.translation import gettext_lazy as _

from comicsdb.models import Series
from comicsdb.views.filter_chips import build_filter_chips, series_type_names

FILTER_LABELS = {
    "q": _("Search"),
    "name": _("Name"),
    "alt_names": _("Alternative Name"),
    "series_type": _("Type"),
    "publisher_name": _("Publisher"),
    "publisher_id": _("Publisher ID"),
    "imprint_name": _("Imprint"),
    "imprint_id": _("Imprint ID"),
    "year_began": _("Year Began"),
    "year_began_gte": _("Year Began (from)"),
    "year_began_lte": _("Year Began (to)"),
    "year_end": _("Year Ended"),
    "status": _("Status"),
    "language": _("Language"),
    "volume": _("Volume"),
}

_STATUS_LABELS = {str(k): v for k, v in Series.Status.choices}
_LANGUAGE_LABELS = dict(global_settings.LANGUAGES)


def build_active_filters(request, type_names=None):
    """Build the series list's filter chips (see ``build_filter_chips``).

    Pass ``type_names`` (a ``{str(id): name}`` dict) to avoid a second DB hit
    when the caller has already fetched SeriesType rows for the filter form.
    """
    display_maps = {
        "series_type": series_type_names(request, type_names),
        "status": _STATUS_LABELS,
        "language": _LANGUAGE_LABELS,
    }
    return build_filter_chips(request, FILTER_LABELS, display_maps)
