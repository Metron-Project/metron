import logging
import operator
from functools import reduce

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, RedirectView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.arc import ArcForm
from comicsdb.forms.attribution import AttributionFormSet
from comicsdb.models.arc import Arc
from comicsdb.models.attribution import Attribution
from comicsdb.models.issue import Issue

PAGINATE = 28
LOGGER = logging.getLogger(__name__)


class ArcList(ListView):
    model = Arc
    paginate_by = PAGINATE
    queryset = Arc.objects.prefetch_related("issues")


class ArcIssueList(ListView):
    template_name = "comicsdb/issue_list.html"
    paginate_by = PAGINATE

    def get_queryset(self):
        self.arc = get_object_or_404(Arc, slug=self.kwargs["slug"])
        return self.arc.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.arc
        return context


class ArcDetail(DetailView):
    model = Arc
    queryset = Arc.objects.select_related("edited_by").prefetch_related(
        Prefetch(
            "issues",
            queryset=Issue.objects.order_by(
                "cover_date", "store_date", "series__sort_name", "number"
            ).select_related("series", "series__series_type"),
        )
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arc = self.get_object()
        try:
            next_arc = Arc.objects.order_by("name").filter(name__gt=arc.name).first()
        except ObjectDoesNotExist:
            next_arc = None

        try:
            previous_arc = Arc.objects.order_by("name").filter(name__lt=arc.name).last()
        except ObjectDoesNotExist:
            previous_arc = None

        context["navigation"] = {"next_arc": next_arc, "previous_arc": previous_arc}
        return context


class ArcDetailRedirect(RedirectView):
    def get_redirect_url(self, pk):
        arc = Arc.objects.get(pk=pk)
        return reverse("arc:detail", kwargs={"slug": arc.slug})


class SearchArcList(ArcList):
    def get_queryset(self):
        result = super().get_queryset()
        if query := self.request.GET.get("q"):
            query_list = query.split()
            result = result.filter(
                reduce(operator.and_, (Q(name__icontains=q) for q in query_list))
            )

        return result


class ArcCreate(LoginRequiredMixin, CreateView):
    model = Arc
    form_class = ArcForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Story Arc"
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

        LOGGER.info("Arc: %s was created by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class ArcUpdate(LoginRequiredMixin, UpdateView):
    model = Arc
    form_class = ArcForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit information for {context['arc']}"
        if self.request.POST:
            context["attribution"] = AttributionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=(Attribution.objects.filter(arcs=self.object)),
                prefix="attribution",
            )
            context["attribution"].full_clean()
        else:
            context["attribution"] = AttributionFormSet(
                instance=self.object,
                queryset=(Attribution.objects.filter(arcs=self.object)),
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

        LOGGER.info("Arc: %s was updated by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class ArcDelete(PermissionRequiredMixin, DeleteView):
    model = Arc
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_arc"
    success_url = reverse_lazy("arc:list")
