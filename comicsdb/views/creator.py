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
from comicsdb.forms.creator import CreatorForm
from comicsdb.models import Creator, Credits, Issue, Series
from comicsdb.models.attribution import Attribution

PAGINATE = 28
LOGGER = logging.getLogger(__name__)


class CreatorSeriesList(ListView):
    paginate_by = PAGINATE
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.series = get_object_or_404(Series, slug=self.kwargs["series"])
        self.creator = get_object_or_404(Creator, slug=self.kwargs["creator"])
        return Issue.objects.select_related("series").filter(
            creators=self.creator, series=self.series
        )


class CreatorIssueList(ListView):
    paginate_by = PAGINATE
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.creator = get_object_or_404(Creator, slug=self.kwargs["slug"])
        return self.creator.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.creator
        return context


class CreatorList(ListView):
    model = Creator
    paginate_by = PAGINATE
    queryset = Creator.objects.prefetch_related("credits_set")


class CreatorDetail(DetailView):
    model = Creator
    queryset = Creator.objects.select_related("edited_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        creator = self.get_object()
        qs = Creator.objects.order_by("name")
        try:
            next_creator = qs.filter(name__gt=creator.name).first()
        except ObjectDoesNotExist:
            next_creator = None

        try:
            previous_creator = qs.filter(name__lt=creator.name).last()
        except ObjectDoesNotExist:
            previous_creator = None

        context["navigation"] = {
            "next_creator": next_creator,
            "previous_creator": previous_creator,
        }

        series_issues = (
            Credits.objects.filter(creator=creator)
            .values(
                "issue__series__name",
                "issue__series__year_began",
                "issue__series__slug",
                "issue__series__series_type",
            )
            .annotate(Count("issue"))
            .order_by("issue__series__sort_name", "issue__series__year_began")
        )
        context["credits"] = series_issues

        return context


class CreatorDetailRedirect(RedirectView):
    def get_redirect_url(self, pk):
        creator = Creator.objects.get(pk=pk)
        return reverse("creator:detail", kwargs={"slug": creator.slug})


class SearchCreatorList(CreatorList):
    def get_queryset(self):
        result = super().get_queryset()
        if query := self.request.GET.get("q"):
            query_list = query.split()
            result = result.filter(
                reduce(
                    operator.and_,
                    (
                        # Unaccent lookup won't work on alias array field.
                        Q(name__unaccent__icontains=q) | Q(alias__icontains=q)
                        for q in query_list
                    ),
                )
            )

        return result


class CreatorCreate(LoginRequiredMixin, CreateView):
    model = Creator
    form_class = CreatorForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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

        LOGGER.info("Creator: %s was created by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class CreatorUpdate(LoginRequiredMixin, UpdateView):
    model = Creator
    form_class = CreatorForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Creator Information"
        if self.request.POST:
            context["attribution"] = AttributionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=(Attribution.objects.filter(creators=self.object)),
                prefix="attribution",
            )
            context["attribution"].full_clean()
        else:
            context["attribution"] = AttributionFormSet(
                instance=self.object,
                queryset=(Attribution.objects.filter(creators=self.object)),
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

            LOGGER.info("Creator: %s was updated by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class CreatorDelete(PermissionRequiredMixin, DeleteView):
    model = Creator
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_creator"
    success_url = reverse_lazy("creator:list")
