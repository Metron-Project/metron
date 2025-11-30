import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from comicsdb.forms.imprint import ImprintForm
from comicsdb.models import Imprint, Series
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


class ImprintList(LoginRequiredMixin, ListView):
    model = Imprint
    paginate_by = PAGINATE_BY
    queryset = Imprint.objects.prefetch_related("series")


class ImprintSeriesList(LoginRequiredMixin, ListView):
    template_name = "comicsdb/series_list.html"
    paginate_by = PAGINATE_BY

    def __init__(self):
        super().__init__()
        self.imprint = None

    def get_queryset(self):
        self.imprint = get_object_or_404(Imprint, slug=self.kwargs["slug"])
        return (
            Series.objects.select_related("series_type")
            .filter(imprint=self.imprint)
            .prefetch_related("issues")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.imprint
        return context


class ImprintDetail(LoginRequiredMixin, NavigationMixin, DetailView):
    model = Imprint
    queryset = Imprint.objects.select_related("edited_by").prefetch_related("series")


class ImprintDetailRedirect(SlugRedirectView):
    model = Imprint
    url_name = "imprint:detail"


class SearchImprintList(SearchMixin, ImprintList):
    pass


class ImprintCreate(AttributionCreateMixin, LoginRequiredMixin, CreateView):
    model = Imprint
    form_class = ImprintForm
    template_name = "comicsdb/model_with_attribution_form.html"
    title = "Add Imprint"


class ImprintUpdate(AttributionUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Imprint
    form_class = ImprintForm
    template_name = "comicsdb/model_with_attribution_form.html"
    attribution_field = "imprints"


class ImprintDelete(PermissionRequiredMixin, DeleteView):
    model = Imprint
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_imprint"
    success_url = reverse_lazy("imprint:list")


class ImprintHistory(HistoryListView):
    model = Imprint
