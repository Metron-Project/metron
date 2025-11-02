import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from comicsdb.forms.universe import UniverseForm
from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from comicsdb.models.universe import Universe
from comicsdb.views.constants import PAGINATE_BY
from comicsdb.views.history import HistoryListView
from comicsdb.views.mixins import (
    AttributionCreateMixin,
    AttributionUpdateMixin,
    NavigationMixin,
    SearchMixin,
    SlugRedirectView,
)

LOGGER = logging.getLogger(__name__)


class UniverseSeriesList(ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.series = get_object_or_404(Series, slug=self.kwargs["series"])
        self.universe = get_object_or_404(Universe, slug=self.kwargs["universe"])

        return Issue.objects.select_related("series").filter(
            universes=self.universe, series=self.series
        )


class UniverseList(ListView):
    model = Universe
    paginate_by = PAGINATE_BY
    queryset = Universe.objects.prefetch_related("issues")


class UniverseIssueList(ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.universe = get_object_or_404(Universe, slug=self.kwargs["slug"])
        return self.universe.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.universe
        return context


class UniverseDetail(NavigationMixin, DetailView):
    model = Universe
    queryset = Universe.objects.select_related("edited_by").prefetch_related(
        Prefetch(
            "issues",
            queryset=Issue.objects.order_by(
                "series__sort_name", "cover_date", "number"
            ).select_related("series", "series__series_type"),
        )
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        universe = self.get_object()

        # Run this context queryset if the issue count is greater than 0.
        if universe.issue_count:
            series_issues = (
                Issue.objects.filter(universes=universe)
                .values(
                    "series__name",
                    "series__year_began",
                    "series__slug",
                    "series__series_type",
                )
                .annotate(issues__count=Count("id"))
                .order_by("series__sort_name", "series__year_began")
            )
            # Rename fields to match template expectations
            context["appearances"] = [
                {
                    "issues__series__name": item["series__name"],
                    "issues__series__year_began": item["series__year_began"],
                    "issues__series__slug": item["series__slug"],
                    "issues__series__series_type": item["series__series_type"],
                    "issues__count": item["issues__count"],
                }
                for item in series_issues
            ]
        else:
            context["appearances"] = ""

        return context


class UniverseDetailRedirect(SlugRedirectView):
    model = Universe
    url_name = "universe:detail"


class SearchUniverseList(SearchMixin, UniverseList):
    def get_search_fields(self):
        # Should we also look up with the unaccent filter? For now, let's not.
        return ["name__icontains", "designation__icontains"]


class UniverseCreate(AttributionCreateMixin, LoginRequiredMixin, CreateView):
    model = Universe
    form_class = UniverseForm
    template_name = "comicsdb/model_with_attribution_form.html"
    title = "Add Universe"


class UniverseUpdate(AttributionUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Universe
    form_class = UniverseForm
    template_name = "comicsdb/model_with_attribution_form.html"
    attribution_field = "universes"


class UniverseDelete(PermissionRequiredMixin, DeleteView):
    model = Universe
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_universe"
    success_url = reverse_lazy("universe:list")


class UniverseHistory(HistoryListView):
    model = Universe
