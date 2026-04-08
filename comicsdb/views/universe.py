import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from comicsdb.forms.universe import UniverseForm
from comicsdb.models import Character, Issue
from comicsdb.models.series import Series
from comicsdb.models.team import Team
from comicsdb.models.universe import Universe
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

_issue_count_sq = (
    Issue.objects.filter(universes=OuterRef("pk"))
    .values("universes")
    .annotate(count=Count("pk"))
    .values("count")
)

_character_count_sq = (
    Character.objects.filter(universes=OuterRef("pk"))
    .values("universes")
    .annotate(count=Count("pk"))
    .values("count")
)

_team_count_sq = (
    Team.objects.filter(universes=OuterRef("pk"))
    .values("universes")
    .annotate(count=Count("pk"))
    .values("count")
)


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
    queryset = Universe.objects.annotate(issue_count=Subquery(_issue_count_sq))


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
    queryset = Universe.objects.select_related("edited_by", "publisher").annotate(
        issue_count=Subquery(_issue_count_sq),
        character_count=Subquery(_character_count_sq),
        team_count=Subquery(_team_count_sq),
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        universe = self.object

        total_issue_count = universe.issue_count or 0
        context["character_count"] = universe.character_count or 0
        context["team_count"] = universe.team_count or 0
        context["total_issue_count"] = total_issue_count

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


class UniverseCharactersLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more characters."""

    model = Universe
    relation_name = "characters"
    template_name = "comicsdb/partials/universe_character_items.html"
    context_object_name = "characters"
    slug_context_name = "universe_slug"


class UniverseTeamsLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more teams."""

    model = Universe
    relation_name = "teams"
    template_name = "comicsdb/partials/universe_team_items.html"
    context_object_name = "teams"
    slug_context_name = "universe_slug"


class UniverseSeriesLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more series appearances."""

    model = Universe
    relation_name = None  # Custom query, not a direct relation
    template_name = "comicsdb/partials/universe_series_items.html"
    context_object_name = "appearances"
    slug_context_name = "universe_slug"

    def get_queryset(self, parent_object, offset, limit):
        """Custom query with annotations and field renaming."""
        series_issues = (
            Issue.objects.filter(universes=parent_object)
            .values(
                "series__name",
                "series__year_began",
                "series__slug",
                "series__series_type",
            )
            .annotate(issues__count=Count("id"))
            .order_by("series__sort_name", "series__year_began")
        )

        paginated_series = series_issues[offset : offset + limit]

        # Rename fields to match template expectations
        return [
            {
                "issues__series__name": item["series__name"],
                "issues__series__year_began": item["series__year_began"],
                "issues__series__slug": item["series__slug"],
                "issues__series__series_type": item["series__series_type"],
                "issues__count": item["issues__count"],
            }
            for item in paginated_series
        ]

    def get_total_count(self, parent_object):
        """Get count of series (not issues)."""
        return (
            Issue.objects.filter(universes=parent_object)
            .values("series__name", "series__year_began", "series__slug", "series__series_type")
            .annotate(issues__count=Count("id"))
            .count()
        )
