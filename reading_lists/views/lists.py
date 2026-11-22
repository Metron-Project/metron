"""Reading list browse, search and per-user list views."""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView

from comicsdb.filters.reading_list import ReadingListViewFilter
from comicsdb.views.filter_chips import build_filter_chips
from comicsdb.views.mixins import SearchMixin
from reading_lists.models import ReadingList

_FILTER_LABELS = {
    "q": _("Search"),
    "name": _("Name"),
    "username": _("Creator"),
    "publisher": _("Publisher"),
    "list_type": _("List Type"),
    "attribution_source": _("Attribution"),
    "average_rating__gte": _("Min Rating"),
    "is_private": _("Privacy"),
}


_RATING_DISPLAY = {
    "1": _("1+ Stars"),
    "2": _("2+ Stars"),
    "3": _("3+ Stars"),
    "4": _("4+ Stars"),
    "5": _("5 Stars"),
}


_PRIVACY_DISPLAY = {"true": _("Private"), "false": _("Public")}


def build_active_filters(request):
    """Build the reading list filter chips (see ``build_filter_chips``)."""
    display_maps = {
        "list_type": dict(ReadingList.ListType.choices),
        "attribution_source": dict(ReadingList.AttributionSource.choices),
        "average_rating__gte": _RATING_DISPLAY,
        "is_private": _PRIVACY_DISPLAY,
    }
    return build_filter_chips(request, _FILTER_LABELS, display_maps)


class ReadingListListView(ListView):
    """Display all public reading lists, plus user's own lists if authenticated."""

    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        queryset = (
            ReadingList.objects.select_related("user")
            .with_list_stats()
            .visible_to(self.request.user)
            .distinct()
        )

        # Apply filters
        filtered = ReadingListViewFilter(self.request.GET, queryset=queryset)
        return filtered.qs.distinct().order_by("name", "attribution_source", "user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["attribution_sources"] = ReadingList.AttributionSource.choices
        context["list_types"] = ReadingList.ListType.choices
        context["has_active_filters"] = any(key != "page" for key in self.request.GET)
        context["active_filters"] = build_active_filters(self.request)
        return context


class SearchReadingListListView(SearchMixin, ReadingListListView):
    """Search reading lists by name, user, or attribution source."""

    def get_search_fields(self):
        """Search across name, username, and attribution source display text."""
        return ["name__icontains", "user__username__icontains", "attribution_source__icontains"]

    def get_queryset(self):
        """Get queryset without applying the filter (SearchMixin handles search)."""
        queryset = (
            ReadingList.objects.select_related("user")
            .with_list_stats()
            .visible_to(self.request.user)
            .distinct()
        )

        # Apply SearchMixin search logic (not the filter)
        if query := self.request.GET.get("q"):
            queryset = self.get_search_queryset(queryset, query)

        return queryset.order_by("name", "attribution_source", "user")


class UserReadingListListView(LoginRequiredMixin, ListView):
    """Display only the current user's reading lists."""

    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_user_view"] = True
        return context

    def get_queryset(self):
        return (
            ReadingList.objects.filter(user=self.request.user)
            .with_list_stats()
            .order_by("name", "attribution_source", "user")
        )
