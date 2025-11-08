import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, View
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.publisher import PublisherForm
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
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


class PublisherList(ListView):
    model = Publisher
    paginate_by = PAGINATE_BY
    queryset = Publisher.objects.prefetch_related("series")


class PublisherSeriesList(ListView):
    template_name = "comicsdb/series_list.html"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        self.publisher = get_object_or_404(Publisher, slug=self.kwargs["slug"])
        return (
            Series.objects.select_related("series_type")
            .filter(publisher=self.publisher)
            .prefetch_related("issues")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.publisher
        return context


class PublisherDetail(NavigationMixin, DetailView):
    model = Publisher
    # Don't prefetch - we'll paginate imprints and universes
    queryset = Publisher.objects.select_related("edited_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        publisher = context["object"]

        # Get counts for imprints and universes
        imprint_count = publisher.imprints.count()
        universe_count = publisher.universes.count()

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


class PublisherImprintsLoadMore(View):
    """HTMX endpoint for lazy loading more imprints."""

    def get(self, request, slug):
        publisher = get_object_or_404(Publisher, slug=slug)
        offset = int(request.GET.get("offset", 0))
        limit = DETAIL_PAGINATE_BY

        imprints = publisher.imprints.all()[offset : offset + limit]
        has_more = publisher.imprints.count() > offset + limit

        context = {
            "imprints": imprints,
            "has_more": has_more,
            "next_offset": offset + limit,
            "publisher_slug": slug,
        }
        return render(request, "comicsdb/partials/publisher_imprint_items.html", context)


class PublisherUniversesLoadMore(View):
    """HTMX endpoint for lazy loading more universes."""

    def get(self, request, slug):
        publisher = get_object_or_404(Publisher, slug=slug)
        offset = int(request.GET.get("offset", 0))
        limit = DETAIL_PAGINATE_BY

        universes = publisher.universes.all()[offset : offset + limit]
        has_more = publisher.universes.count() > offset + limit

        context = {
            "universes": universes,
            "has_more": has_more,
            "next_offset": offset + limit,
            "publisher_slug": slug,
        }
        return render(request, "comicsdb/partials/publisher_universe_items.html", context)
