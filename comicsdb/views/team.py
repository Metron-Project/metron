import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.team import TeamForm
from comicsdb.models.team import Team
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


class TeamList(LoginRequiredMixin, ListView):
    model = Team
    paginate_by = PAGINATE_BY
    queryset = Team.objects.prefetch_related("issues")


class TeamIssueList(LoginRequiredMixin, ListView):
    paginate_by = PAGINATE_BY
    template_name = "comicsdb/issue_list.html"

    def get_queryset(self):
        self.team = get_object_or_404(Team, slug=self.kwargs["slug"])
        return self.team.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.team
        return context


class TeamDetail(LoginRequiredMixin, NavigationMixin, DetailView):
    model = Team
    # Don't prefetch issues - only need member count
    queryset = Team.objects.select_related("edited_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        team = context["object"]

        # Get member count and paginate
        member_count = team.characters.count()
        context["member_count"] = member_count

        # Only load first batch of members
        if member_count > 0:
            context["members"] = team.characters.all()[:DETAIL_PAGINATE_BY]

        return context


class TeamDetailRedirect(SlugRedirectView):
    model = Team
    url_name = "team:detail"


class SearchTeamList(SearchMixin, TeamList):
    pass


class TeamCreate(AttributionCreateMixin, LoginRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    template_name = "comicsdb/model_with_attribution_form.html"
    title = "Add Team"


class TeamUpdate(AttributionUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Team
    form_class = TeamForm
    template_name = "comicsdb/model_with_attribution_form.html"
    attribution_field = "teams"


class TeamDelete(PermissionRequiredMixin, DeleteView):
    model = Team
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_team"
    success_url = reverse_lazy("team:list")


class TeamHistory(HistoryListView):
    model = Team


class TeamMembersLoadMore(LoginRequiredMixin, LazyLoadMixin):
    """HTMX endpoint for lazy loading more team members."""

    model = Team
    relation_name = "characters"
    template_name = "comicsdb/partials/team_member_items.html"
    context_object_name = "members"
    slug_context_name = "team_slug"
