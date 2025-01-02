import logging
import operator
from functools import reduce

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, RedirectView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.attribution import AttributionFormSet
from comicsdb.forms.publisher import PublisherForm
from comicsdb.models.attribution import Attribution
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series

PAGINATE = 28
LOGGER = logging.getLogger(__name__)


class PublisherList(ListView):
    model = Publisher
    paginate_by = PAGINATE
    queryset = Publisher.objects.prefetch_related("series")


class PublisherSeriesList(ListView):
    template_name = "comicsdb/series_list.html"
    paginate_by = PAGINATE

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


class PublisherDetail(DetailView):
    model = Publisher
    queryset = Publisher.objects.select_related("edited_by").prefetch_related(
        "series", "universes__issues", "imprints__series"
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        publisher = self.get_object()
        try:
            next_publisher = (
                Publisher.objects.order_by("name").filter(name__gt=publisher.name).first()
            )
        except ObjectDoesNotExist:
            next_publisher = None

        try:
            previous_publisher = (
                Publisher.objects.order_by("name").filter(name__lt=publisher.name).last()
            )
        except ObjectDoesNotExist:
            previous_publisher = None

        context["navigation"] = {
            "next_publisher": next_publisher,
            "previous_publisher": previous_publisher,
        }
        return context


class PublisherDetailRedirect(RedirectView):
    def get_redirect_url(self, pk):
        publisher = Publisher.objects.get(pk=pk)
        return reverse("character:detail", kwargs={"slug": publisher.slug})


class SearchPublisherList(PublisherList):
    def get_queryset(self):
        result = super().get_queryset()
        if query := self.request.GET.get("q"):
            query_list = query.split()
            result = result.filter(
                reduce(operator.and_, (Q(name__icontains=q) for q in query_list))
            )

        return result


class PublisherCreate(LoginRequiredMixin, CreateView):
    model = Publisher
    form_class = PublisherForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Publisher"
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

        LOGGER.info("Publisher: %s was created by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class PublisherUpdate(LoginRequiredMixin, UpdateView):
    model = Publisher
    form_class = PublisherForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit information for {context['publisher']}"
        if self.request.POST:
            context["attribution"] = AttributionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=(Attribution.objects.filter(publishers=self.object)),
                prefix="attribution",
            )
            context["attribution"].full_clean()
        else:
            context["attribution"] = AttributionFormSet(
                instance=self.object,
                queryset=(Attribution.objects.filter(publishers=self.object)),
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

            LOGGER.info(
                "Publisher: %s was updated by %s", form.instance.name, self.request.user
            )
        return super().form_valid(form)


class PublisherDelete(PermissionRequiredMixin, DeleteView):
    model = Publisher
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_publisher"
    success_url = reverse_lazy("publisher:list")
