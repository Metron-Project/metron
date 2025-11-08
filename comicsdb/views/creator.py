import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.creator import CreatorForm
from comicsdb.models import Creator, Credits, Issue, Series
from comicsdb.views.constants import DETAIL_PAGINATE_BY, PAGINATE_BY
from comicsdb.views.history import HistoryListView
from comicsdb.views.mixins import (
    AttributionCreateMixin,
    AttributionUpdateMixin,
    LazyLoadMixin,
    NavigationMixin,
    SearchMixin,
    SlugRedirectView,
)

LOGGER = logging.getLogger(__name__)


class CreatorSeriesList(ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.series = get_object_or_404(Series, slug=self.kwargs["series"])
        self.creator = get_object_or_404(Creator, slug=self.kwargs["creator"])
        return Issue.objects.select_related("series").filter(
            creators=self.creator, series=self.series
        )


class CreatorIssueList(ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.creator = get_object_or_404(Creator, slug=self.kwargs["slug"])
        return self.creator.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.creator
        return context


class CreatorList(ListView):
    model = Creator
    paginate_by = PAGINATE_BY
    queryset = Creator.objects.prefetch_related("credits_set")


class CreatorDetail(NavigationMixin, DetailView):
    model = Creator
    queryset = Creator.objects.select_related("edited_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        creator = context["object"]

        series_issues = (
            Credits.objects.filter(creator=creator)
            .values(
                "issue__series__name",
                "issue__series__year_began",
                "issue__series__slug",
                "issue__series__series_type",
                "issue__series__sort_name",  # Include for ordering
            )
            .annotate(issue__count=Count("issue"))
            .order_by("issue__series__sort_name", "issue__series__year_began")
        )

        # Get total count for pagination
        total_series_count = series_issues.count()
        context["series_count"] = total_series_count

        # Only get first batch for initial load
        context["credits"] = series_issues[:DETAIL_PAGINATE_BY]

        return context


class CreatorDetailRedirect(SlugRedirectView):
    model = Creator
    url_name = "creator:detail"


class SearchCreatorList(SearchMixin, CreatorList):
    def get_search_fields(self):
        # Unaccent lookup won't work on alias array field.
        return ["name__unaccent__icontains", "alias__icontains"]


class CreatorCreate(AttributionCreateMixin, LoginRequiredMixin, CreateView):
    model = Creator
    form_class = CreatorForm
    template_name = "comicsdb/model_with_attribution_form.html"


class CreatorUpdate(AttributionUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Creator
    form_class = CreatorForm
    template_name = "comicsdb/model_with_attribution_form.html"
    attribution_field = "creators"

    def get_title(self):
        return "Edit Creator Information"


class CreatorDelete(PermissionRequiredMixin, DeleteView):
    model = Creator
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_creator"
    success_url = reverse_lazy("creator:list")


class CreatorHistory(HistoryListView):
    model = Creator


class CreatorSeriesLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more series credits."""

    model = Creator
    relation_name = None  # Custom query, not a direct relation
    template_name = "comicsdb/partials/creator_series_items.html"
    context_object_name = "credits"
    slug_context_name = "creator_slug"

    def get_queryset(self, parent_object, offset, limit):
        """Custom query with annotations."""
        series_issues = (
            Credits.objects.filter(creator=parent_object)
            .values(
                "issue__series__name",
                "issue__series__year_began",
                "issue__series__slug",
                "issue__series__series_type",
                "issue__series__sort_name",  # Include for ordering
            )
            .annotate(issue__count=Count("issue"))
            .order_by("issue__series__sort_name", "issue__series__year_began")
        )
        return series_issues[offset : offset + limit]

    def get_total_count(self, parent_object):
        """Get count of series credits."""
        return (
            Credits.objects.filter(creator=parent_object)
            .values(
                "issue__series__name",
                "issue__series__year_began",
                "issue__series__slug",
                "issue__series__series_type",
            )
            .annotate(issue__count=Count("issue"))
            .count()
        )
