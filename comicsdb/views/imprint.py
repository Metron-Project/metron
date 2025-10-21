import logging
import operator
from functools import reduce

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    RedirectView,
    UpdateView,
)

from comicsdb.forms.attribution import AttributionFormSet
from comicsdb.forms.imprint import ImprintForm
from comicsdb.models import Attribution, Imprint, Series

PAGINATE = 28
LOGGER = logging.getLogger(__name__)


class ImprintList(ListView):
    model = Imprint
    paginate_by = PAGINATE
    queryset = Imprint.objects.prefetch_related("series")


class ImprintSeriesList(ListView):
    template_name = "comicsdb/series_list.html"
    paginate_by = PAGINATE

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


class ImprintDetail(DetailView):
    model = Imprint
    queryset = Imprint.objects.select_related("edited_by").prefetch_related("series")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        imprint = self.get_object()
        try:
            next_imprint = (
                Imprint.objects.order_by("name").filter(name__gt=imprint.name).first()
            )
        except ObjectDoesNotExist:
            next_imprint = None

        try:
            previous_imprint = (
                Imprint.objects.order_by("name").filter(name__lt=imprint.name).last()
            )
        except ObjectDoesNotExist:
            previous_imprint = None

        context["navigation"] = {
            "next_imprint": next_imprint,
            "previous_imprint": previous_imprint,
        }
        return context


class ImprintDetailRedirect(RedirectView):
    def get_redirect_url(self, pk):
        imprint = Imprint.objects.get(pk=pk)
        return reverse("imprint:detail", kwargs={"slug": imprint.slug})


class SearchImprintList(ImprintList):
    def get_queryset(self):
        result = super().get_queryset()
        if query := self.request.GET.get("q"):
            query_list = query.split()
            result = result.filter(
                reduce(operator.and_, (Q(name__icontains=q) for q in query_list))
            )

        return result


class ImprintCreate(LoginRequiredMixin, CreateView):
    model = Imprint
    form_class = ImprintForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Imprint"
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

        LOGGER.info("Imprint: %s was created by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class ImprintUpdate(LoginRequiredMixin, UpdateView):
    model = Imprint
    form_class = ImprintForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit information for {context['imprint']}"
        if self.request.POST:
            context["attribution"] = AttributionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=(Attribution.objects.filter(imprints=self.object)),
                prefix="attribution",
            )
            context["attribution"].full_clean()
        else:
            context["attribution"] = AttributionFormSet(
                instance=self.object,
                queryset=(Attribution.objects.filter(imprints=self.object)),
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

            LOGGER.info("Imprint: %s was updated by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class ImprintDelete(PermissionRequiredMixin, DeleteView):
    model = Imprint
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_imprint"
    success_url = reverse_lazy("imprint:list")
