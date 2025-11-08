import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.character import CharacterForm
from comicsdb.models import Character, Issue, Series
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


class CharacterSeriesList(ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.series = get_object_or_404(Series, slug=self.kwargs["series"])
        self.character = get_object_or_404(Character, slug=self.kwargs["character"])

        return Issue.objects.select_related("series").filter(
            characters=self.character, series=self.series
        )


class CharacterList(ListView):
    model = Character
    paginate_by = PAGINATE_BY
    queryset = Character.objects.prefetch_related("issues")


class CharacterIssueList(ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.character = get_object_or_404(Character, slug=self.kwargs["slug"])
        return self.character.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.character
        return context


class CharacterDetail(NavigationMixin, DetailView):
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


class CharacterSeriesLoadMore(View):
    """HTMX endpoint for lazy loading more series appearances."""

    def get(self, request, slug):
        character = get_object_or_404(Character, slug=slug)
        offset = int(request.GET.get("offset", 0))
        limit = DETAIL_PAGINATE_BY

        # Same query as in CharacterDetail.get_context_data
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
            "character_slug": slug,
        }
        return render(request, "comicsdb/partials/character_series_items.html", context)
