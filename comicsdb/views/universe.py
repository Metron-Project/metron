import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from comicsdb.forms.universe import UniverseForm
from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from comicsdb.models.universe import Universe
from comicsdb.views.constants import DETAIL_PAGINATE_BY, PAGINATE_BY
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
    # Don't use expensive COUNT DISTINCT in queryset - calculate in get_context_data instead
    queryset = Universe.objects.select_related("edited_by", "publisher")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        universe = context["object"]  # Use the object from context, not get_object()

        # Get counts with simple, fast queries instead of expensive COUNT DISTINCT
        # These are much faster than annotating on the queryset
        character_count = universe.characters.count()
        team_count = universe.teams.count()
        total_issue_count = universe.issues.count()

        # Add counts to context
        context["character_count"] = character_count
        context["team_count"] = team_count
        context["total_issue_count"] = total_issue_count

        # Also add to object for template compatibility
        universe.character_count = character_count
        universe.team_count = team_count
        universe.total_issue_count = total_issue_count

        # Run this context queryset if the issue count is greater than 0.
        if total_issue_count:
            series_issues = (
                Issue.objects.filter(universes=universe)
                .values(
                    "series__name",
                    "series__year_began",
                    "series__slug",
                    "series__series_type",
                    "series__sort_name",  # Include for ordering
                )
                .annotate(issues__count=Count("id"))
                .order_by("series__sort_name", "series__year_began")
            )

            # Get total count for pagination
            total_series_count = series_issues.count()
            context["series_count"] = total_series_count

            # Only get first batch for initial load
            paginated_series = series_issues[:DETAIL_PAGINATE_BY]

            # Rename fields to match template expectations
            context["appearances"] = [
                {
                    "issues__series__name": item["series__name"],
                    "issues__series__year_began": item["series__year_began"],
                    "issues__series__slug": item["series__slug"],
                    "issues__series__series_type": item["series__series_type"],
                    "issues__count": item["issues__count"],
                }
                for item in paginated_series
            ]
        else:
            context["appearances"] = ""
            context["series_count"] = 0

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


class UniverseCharactersLoadMore(View):
    """HTMX endpoint for lazy loading more characters."""

    def get(self, request, slug):
        universe = get_object_or_404(Universe, slug=slug)
        offset = int(request.GET.get("offset", 0))
        limit = DETAIL_PAGINATE_BY

        characters = universe.characters.all()[offset : offset + limit]
        has_more = universe.characters.count() > offset + limit

        context = {
            "characters": characters,
            "has_more": has_more,
            "next_offset": offset + limit,
            "universe_slug": slug,
        }
        return render(request, "comicsdb/partials/universe_character_items.html", context)


class UniverseTeamsLoadMore(View):
    """HTMX endpoint for lazy loading more teams."""

    def get(self, request, slug):
        universe = get_object_or_404(Universe, slug=slug)
        offset = int(request.GET.get("offset", 0))
        limit = DETAIL_PAGINATE_BY

        teams = universe.teams.all()[offset : offset + limit]
        has_more = universe.teams.count() > offset + limit

        context = {
            "teams": teams,
            "has_more": has_more,
            "next_offset": offset + limit,
            "universe_slug": slug,
        }
        return render(request, "comicsdb/partials/universe_team_items.html", context)


class UniverseSeriesLoadMore(View):
    """HTMX endpoint for lazy loading more series appearances."""

    def get(self, request, slug):
        universe = get_object_or_404(Universe, slug=slug)
        offset = int(request.GET.get("offset", 0))
        limit = DETAIL_PAGINATE_BY

        # Same query as in UniverseDetail.get_context_data
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

        total_count = series_issues.count()
        paginated_series = series_issues[offset : offset + limit]

        # Rename fields to match template expectations
        appearances = [
            {
                "issues__series__name": item["series__name"],
                "issues__series__year_began": item["series__year_began"],
                "issues__series__slug": item["series__slug"],
                "issues__series__series_type": item["series__series_type"],
                "issues__count": item["issues__count"],
            }
            for item in paginated_series
        ]

        has_more = total_count > offset + limit

        context = {
            "appearances": appearances,
            "has_more": has_more,
            "next_offset": offset + limit,
            "universe_slug": slug,
        }
        return render(request, "comicsdb/partials/universe_series_items.html", context)
