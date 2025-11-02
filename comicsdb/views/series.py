import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.series import SeriesForm
from comicsdb.models import Series
from comicsdb.views.constants import PAGINATE_BY
from comicsdb.views.history import HistoryListView
from comicsdb.views.mixins import (
    AttributionCreateMixin,
    AttributionUpdateMixin,
    SearchMixin,
    SlugRedirectView,
)

LOGGER = logging.getLogger(__name__)


class SeriesList(ListView):
    model = Series
    paginate_by = PAGINATE_BY
    queryset = Series.objects.select_related("series_type").prefetch_related("issues")


class SeriesIssueList(ListView):
    template_name = "comicsdb/issue_list.html"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        self.series = get_object_or_404(Series, slug=self.kwargs["slug"])
        return self.series.issues.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.series
        return context


class SeriesDetail(DetailView):
    model = Series
    queryset = Series.objects.select_related(
        "publisher", "imprint", "edited_by", "series_type"
    ).prefetch_related("issues")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = self.get_object()

        # Set the initial value for the navigation variables
        next_series = None
        previous_series = None

        # Create the base queryset with all the series.
        qs = Series.objects.all().order_by("sort_name", "year_began")

        # Determine if there is more than 1 series with the same name
        series_count = qs.filter(sort_name__gte=series.sort_name).count()

        # If there is more than one series with the same name
        # let's attempt to get the next and previous items
        if series_count > 1:
            try:
                next_series = qs.filter(
                    sort_name=series.sort_name, year_began__gt=series.year_began
                ).first()
            except ObjectDoesNotExist:
                next_series = None

            try:
                previous_series = qs.filter(
                    sort_name=series.sort_name, year_began__lt=series.year_began
                ).last()
            except ObjectDoesNotExist:
                previous_series = None

        if not next_series:
            try:
                next_series = qs.filter(sort_name__gt=series.sort_name).first()
            except ObjectDoesNotExist:
                next_series = None

        if not previous_series:
            try:
                previous_series = qs.filter(sort_name__lt=series.sort_name).last()
            except ObjectDoesNotExist:
                previous_series = None

        # Top 10 creator credits for series. Might be worthwhile to exclude editors, etc.
        creators = (
            series.issues.values("creators__name", "creators__image", "creators__slug")
            .order_by("creators")
            .annotate(count=Count("creators"))
            .order_by("-count", "creators__name")
            .filter(count__gte=1)[:12]
        )

        # Top 10 character appearances for series.
        characters = (
            series.issues.values("characters__name", "characters__image", "characters__slug")
            .order_by("characters")
            .annotate(count=Count("characters"))
            .order_by("-count", "characters__name")
            .filter(count__gte=1)[:12]
        )

        context["navigation"] = {
            "next_series": next_series,
            "previous_series": previous_series,
        }
        context["creators"] = creators
        context["characters"] = characters
        return context


class SeriesDetailRedirect(SlugRedirectView):
    model = Series
    url_name = "series:detail"


class SearchSeriesList(SearchMixin, SeriesList):
    def get_search_fields(self):
        return ["name__unaccent__icontains"]


class SeriesCreate(AttributionCreateMixin, LoginRequiredMixin, CreateView):
    model = Series
    form_class = SeriesForm
    template_name = "comicsdb/model_with_attribution_form.html"
    title = "Add Series"


class SeriesUpdate(AttributionUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Series
    form_class = SeriesForm
    template_name = "comicsdb/model_with_attribution_form.html"
    attribution_field = "series"


class SeriesDelete(PermissionRequiredMixin, DeleteView):
    model = Series
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_series"
    success_url = reverse_lazy("series:list")


class SeriesHistory(HistoryListView):
    model = Series
