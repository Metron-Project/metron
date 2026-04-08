import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, OuterRef, Subquery
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.publisher import PublisherForm
from comicsdb.models.imprint import Imprint
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
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
    Issue.objects.filter(series=OuterRef("pk"))
    .values("series")
    .annotate(count=Count("pk"))
    .values("count")
)

_series_count_sq = (
    Series.objects.filter(publisher=OuterRef("pk"))
    .values("publisher")
    .annotate(count=Count("pk"))
    .values("count")
)

_imprint_count_sq = (
    Imprint.objects.filter(publisher=OuterRef("pk"))
    .values("publisher")
    .annotate(count=Count("pk"))
    .values("count")
)

_universe_count_sq = (
    Universe.objects.filter(publisher=OuterRef("pk"))
    .values("publisher")
    .annotate(count=Count("pk"))
    .values("count")
)


class PublisherList(ListView):
    model = Publisher
    paginate_by = PAGINATE_BY
    queryset = Publisher.objects.annotate(series_count=Subquery(_series_count_sq)).order_by("name")


class PublisherSeriesList(ListView):
    template_name = "comicsdb/series_list.html"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        self.publisher = get_object_or_404(Publisher, slug=self.kwargs["slug"])
        return (
            Series.objects.select_related("series_type")
            .filter(publisher=self.publisher)
            .prefetch_related("issues")
            .annotate(issue_count=Subquery(_issue_count_sq))
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.publisher
        return context


class PublisherDetail(NavigationMixin, DetailView):
    model = Publisher
    # Don't prefetch - we'll paginate imprints and universes
    queryset = Publisher.objects.select_related("edited_by").annotate(
        imprint_count=Subquery(_imprint_count_sq),
        universe_count=Subquery(_universe_count_sq),
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        publisher = context["object"]

        imprint_count = publisher.imprint_count or 0
        universe_count = publisher.universe_count or 0

        context["imprint_count"] = imprint_count
        context["universe_count"] = universe_count

        # Paginate imprints - only load first batch
        if imprint_count > 0:
            context["imprints"] = publisher.imprints.all()[:DETAIL_PAGINATE_BY]

        # Paginate universes - only load first batch
        if universe_count > 0:
            context["universes"] = publisher.universes.all()[:DETAIL_PAGINATE_BY]

        return context


class PublisherDetailRedirect(SlugRedirectView):
    model = Publisher
    url_name = "publisher:detail"


class SearchPublisherList(SearchMixin, PublisherList):
    pass


class PublisherCreate(AttributionCreateMixin, LoginRequiredMixin, CreateView):
    model = Publisher
    form_class = PublisherForm
    template_name = "comicsdb/model_with_attribution_form.html"
    title = "Add Publisher"


class PublisherUpdate(AttributionUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Publisher
    form_class = PublisherForm
    template_name = "comicsdb/model_with_attribution_form.html"
    attribution_field = "publishers"


class PublisherDelete(PermissionRequiredMixin, DeleteView):
    model = Publisher
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_publisher"
    success_url = reverse_lazy("publisher:list")


class PublisherHistory(HistoryListView):
    model = Publisher


class PublisherImprintsLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more imprints."""

    model = Publisher
    relation_name = "imprints"
    template_name = "comicsdb/partials/publisher_imprint_items.html"
    context_object_name = "imprints"
    slug_context_name = "publisher_slug"


class PublisherUniversesLoadMore(LazyLoadMixin):
    """HTMX endpoint for lazy loading more universes."""

    model = Publisher
    relation_name = "universes"
    template_name = "comicsdb/partials/publisher_universe_items.html"
    context_object_name = "universes"
    slug_context_name = "publisher_slug"
