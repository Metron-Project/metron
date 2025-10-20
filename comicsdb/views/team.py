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
from comicsdb.forms.team import TeamForm
from comicsdb.models.attribution import Attribution
from comicsdb.models.team import Team

PAGINATE = 28
LOGGER = logging.getLogger(__name__)


class TeamList(ListView):
    model = Team
    paginate_by = PAGINATE
    queryset = Team.objects.prefetch_related("issues")

    def get_template_names(self):
        # If this is an HTMX request, return only the partial content
        if self.request.headers.get("HX-Request"):
            return ["comicsdb/partials/generic_list_content.html"]
        return ["comicsdb/team_list.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add required context for generic template
        context["list_items"] = context["team_list"]
        context["list_name"] = "team"
        context["list_title"] = "Team"
        context["search_url"] = "team:search"
        context["search_placeholder"] = "Find a team"
        context["create_url"] = "team:create"
        context["create_title"] = "Add a new team"
        context["detail_url_name"] = "team:detail"
        context["image_ratio"] = "is-2by3"
        context["default_image"] = "site/img/image-not-found.webp"
        context["count_url_name"] = "team:issue"
        context["count_label"] = "Issue"
        return context


class TeamIssueList(ListView):
    paginate_by = PAGINATE
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.team = get_object_or_404(Team, slug=self.kwargs["slug"])
        return self.team.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.team
        return context


class TeamDetail(DetailView):
    model = Team
    queryset = Team.objects.select_related("edited_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = self.get_object()
        try:
            next_team = Team.objects.filter(name__gt=team.name).order_by("name").first()
        except ObjectDoesNotExist:
            next_team = None

        try:
            previous_team = Team.objects.filter(name__lt=team.name).order_by("name").last()
        except ObjectDoesNotExist:
            previous_team = None

        context["navigation"] = {"next_team": next_team, "previous_team": previous_team}
        return context


class TeamDetailRedirect(RedirectView):
    def get_redirect_url(self, pk):
        team = Team.objects.get(pk=pk)
        return reverse("team:detail", kwargs={"slug": team.slug})


class SearchTeamList(TeamList):
    def get_queryset(self):
        result = super().get_queryset()
        if query := self.request.GET.get("q"):
            query_list = query.split()
            result = result.filter(
                reduce(operator.and_, (Q(name__icontains=q) for q in query_list))
            )

        return result


class TeamCreate(LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Add Team"
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

        LOGGER.info("Team: %s was created by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class TeamUpdate(LoginRequiredMixin, UpdateView):
    model = Team
    form_class = TeamForm
    template_name = "comicsdb/model_with_attribution_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = f"Edit information for {context['team']}"
        if self.request.POST:
            context["attribution"] = AttributionFormSet(
                self.request.POST,
                instance=self.object,
                queryset=(Attribution.objects.filter(teams=self.object)),
                prefix="attribution",
            )
            context["attribution"].full_clean()
        else:
            context["attribution"] = AttributionFormSet(
                instance=self.object,
                queryset=(Attribution.objects.filter(teams=self.object)),
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

        LOGGER.info("Team: %s was updated by %s", form.instance.name, self.request.user)
        return super().form_valid(form)


class TeamDelete(PermissionRequiredMixin, DeleteView):
    model = Team
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_team"
    success_url = reverse_lazy("team:list")
