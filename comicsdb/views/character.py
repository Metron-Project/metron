import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.character import CharacterForm
from comicsdb.models import Character, Issue, Series
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
    queryset = Character.objects.select_related("edited_by").prefetch_related(
        Prefetch(
            "issues",
            queryset=Issue.objects.order_by(
                "series__sort_name", "cover_date", "number"
            ).select_related("series", "series__series_type"),
        )
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        character = self.get_object()

        # TODO: Look into improving this queryset
        #
        # Run this context queryset if the issue count is greater than 0.
        if character.issue_count:
            series_issues = (
                Character.objects.filter(id=character.id)
                .values(
                    "issues__series__name",
                    "issues__series__year_began",
                    "issues__series__slug",
                    "issues__series__series_type",
                )
                .annotate(Count("issues"))
                .order_by("issues__series__sort_name", "issues__series__year_began")
            )
            context["appearances"] = series_issues
        else:
            context["appearances"] = ""

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
