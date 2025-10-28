import logging
import operator
from functools import reduce

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, RedirectView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.attribution import AttributionFormSet
from comicsdb.forms.series import SeriesForm
from comicsdb.models import Series
from comicsdb.models.attribution import Attribution
from comicsdb.views.history import HistoryListView

PAGINATE = 28
LOGGER = logging.getLogger(__name__)


class SeriesList(ListView):
    model = Series
    paginate_by = PAGINATE
    queryset = Series.objects.select_related("series_type").prefetch_related("issues")


class SeriesIssueList(ListView):
    template_name = "comicsdb/issue_list.html"
    paginate_by = PAGINATE

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


class SeriesDetailRedirect(RedirectView):
    def get_redirect_url(self, pk):
        series = Series.objects.get(pk=pk)
        return reverse("series:detail", kwargs={"slug": series.slug})


class SearchSeriesList(SeriesList):
    def get_queryset(self):
        result = super().get_queryset()
        if query := self.request.GET.get("q"):
            query_list = query.split()
            result = result.filter(
                reduce(operator.and_, (Q(name__unaccent__icontains=q) for q in query_list))
            )

        return result


class SeriesCreate(LoginRequiredMixin, CreateView):
    model = Series
    form_class = SeriesForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Series"
        if self.request.POST:
            context["attribution"] = AttributionFormSet(self.request.POST)
        else:
            context["attribution"] = AttributionFormSet()
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        attribution_form = context["attribution"]
        with transaction.atomic():
            form.instance.created_by = self.request.user
            form.instance.edited_by = self.request.user
            if attribution_form.is_valid():
                self.object = form.save()
                attribution_form.instance = self.object
                attribution_form.save()
            else:
                return super().form_invalid(form)

        LOGGER.info("Series: %s was created by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class SeriesUpdate(LoginRequiredMixin, UpdateView):
    model = Series
    form_class = SeriesForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit information for {context['series']}"
        if self.request.POST:
            context["attribution"] = AttributionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=(Attribution.objects.filter(series=self.object)),
                prefix="attribution",
            )
            context["attribution"].full_clean()
        else:
            context["attribution"] = AttributionFormSet(
                instance=self.object,
                queryset=(Attribution.objects.filter(series=self.object)),
                prefix="attribution",
            )
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        attribution_form = context["attribution"]
        with transaction.atomic():
            form.instance.edited_by = self.request.user
            if attribution_form.is_valid():
                self.object = form.save(commit=False)
                attribution_form.instance = self.object
                attribution_form.save()
            else:
                return super().form_invalid(form)

        LOGGER.info("Series: %s was updated by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class SeriesDelete(PermissionRequiredMixin, DeleteView):
    model = Series
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_series"
    success_url = reverse_lazy("series:list")


class SeriesHistory(HistoryListView):
    model = Series
