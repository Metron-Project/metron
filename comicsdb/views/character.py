import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.character import CharacterForm
from comicsdb.models import Character, Issue, Series
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


class CharacterSeriesList(LoginRequiredMixin, ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.series = get_object_or_404(Series, slug=self.kwargs["series"])
        self.character = get_object_or_404(Character, slug=self.kwargs["character"])

        return Issue.objects.select_related("series").filter(
            characters=self.character, series=self.series
        )


class CharacterList(LoginRequiredMixin, ListView):
    model = Character
    paginate_by = PAGINATE_BY
    queryset = Character.objects.prefetch_related("issues")


class CharacterIssueList(LoginRequiredMixin, ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.character = get_object_or_404(Character, slug=self.kwargs["slug"])
        return self.character.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.character
        return context


class CharacterDetail(LoginRequiredMixin, NavigationMixin, DetailView):
    model = Character
    # Don't prefetch issues - we only need series aggregates, not all issue objects
    queryset = Character.objects.select_related("edited_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        character = context["object"]  # Use the object from context, not get_object()

        # Run this context queryset if the issue count is greater than 0.
        if character.issue_count:
            series_issues = (
                Issue.objects.filter(characters=character)
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


class CharacterDetailRedirect(SlugRedirectView):
    model = Character
    url_name = "character:detail"


class SearchCharacterList(SearchMixin, CharacterList):
    def get_search_fields(self):
        # Unaccent lookup won't work on alias array field.
        return ["name__unaccent__icontains", "alias__icontains"]


class CharacterCreate(AttributionCreateMixin, LoginRequiredMixin, CreateView):
    model = Character
    form_class = CharacterForm
    template_name = "comicsdb/model_with_attribution_form.html"
    title = "Add Character"


class CharacterUpdate(AttributionUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Character
    form_class = CharacterForm
    template_name = "comicsdb/model_with_attribution_form.html"
    attribution_field = "characters"


class CharacterDelete(PermissionRequiredMixin, DeleteView):
    model = Character
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_character"
    success_url = reverse_lazy("character:list")


class CharacterHistory(HistoryListView):
    model = Character


class CharacterSeriesLoadMore(LoginRequiredMixin, LazyLoadMixin):
    """HTMX endpoint for lazy loading more series appearances."""

    model = Character
    relation_name = None  # Custom query, not a direct relation
    template_name = "comicsdb/partials/character_series_items.html"
    context_object_name = "appearances"
    slug_context_name = "character_slug"

    def get_queryset(self, parent_object, offset, limit):
        """Custom query with annotations and field renaming."""
        series_issues = (
            Issue.objects.filter(characters=parent_object)
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
            Issue.objects.filter(characters=parent_object)
            .values("series__name", "series__year_began", "series__slug", "series__series_type")
            .annotate(issues__count=Count("id"))
            .count()
        )
