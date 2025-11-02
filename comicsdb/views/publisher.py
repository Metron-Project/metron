import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.publisher import PublisherForm
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series
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
    queryset = Publisher.objects.select_related("edited_by").prefetch_related(
        Prefetch("series", queryset=Series.objects.select_related("series_type")),
        Prefetch("imprints__series", queryset=Series.objects.select_related("series_type")),
    )


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
