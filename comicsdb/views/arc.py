import logging

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from comicsdb.forms.arc import ArcForm
from comicsdb.models.arc import Arc
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


class ArcList(ListView):
    model = Arc
    paginate_by = PAGINATE_BY
    queryset = Arc.objects.prefetch_related("issues")


class ArcIssueList(ListView):
    template_name = "comicsdb/issue_list.html"
    paginate_by = PAGINATE_BY

    def get_queryset(self):
        self.arc = get_object_or_404(Arc, slug=self.kwargs["slug"])
        return self.arc.issues.all().select_related("series", "series__series_type")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = self.arc
        return context


class ArcDetail(NavigationMixin, DetailView):
    model = Arc
    queryset = Arc.objects.select_related("edited_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        arc = context["object"]

        # Get issue count and paginate
        issue_count = arc.issues.count()
        context["issue_count"] = issue_count

        # Only load first 30 issues
        if issue_count > 0:
            issues_qs = arc.issues.order_by(
                "cover_date", "store_date", "series__sort_name", "number"
            ).select_related("series", "series__series_type")
            context["issues"] = issues_qs[:30]

        return context


class ArcDetailRedirect(SlugRedirectView):
    model = Arc
    url_name = "arc:detail"


class SearchArcList(SearchMixin, ArcList):
    pass


class ArcCreate(AttributionCreateMixin, LoginRequiredMixin, CreateView):
    model = Arc
    form_class = ArcForm
    template_name = "comicsdb/model_with_attribution_form.html"
    title = "Add Story Arc"


class ArcUpdate(AttributionUpdateMixin, LoginRequiredMixin, UpdateView):
    model = Arc
    form_class = ArcForm
    template_name = "comicsdb/model_with_attribution_form.html"
    attribution_field = "arcs"


class ArcDelete(PermissionRequiredMixin, DeleteView):
    model = Arc
    template_name = "comicsdb/confirm_delete.html"
    permission_required = "comicsdb.delete_arc"
    success_url = reverse_lazy("arc:list")


class ArcHistory(HistoryListView):
    model = Arc


class ArcIssuesLoadMore(View):
    """HTMX endpoint for lazy loading more arc issues."""

    def get(self, request, slug):
        arc = get_object_or_404(Arc, slug=slug)
        offset = int(request.GET.get("offset", 0))
        limit = 30  # Load 30 items at a time

        # Same query as in ArcDetail.get_context_data
        issues_qs = arc.issues.order_by(
            "cover_date", "store_date", "series__sort_name", "number"
        ).select_related("series", "series__series_type")

        total_count = issues_qs.count()
        paginated_issues = issues_qs[offset : offset + limit]

        has_more = total_count > offset + limit

        context = {
            "issues": paginated_issues,
            "has_more": has_more,
            "next_offset": offset + limit,
            "arc_slug": slug,
        }
        return render(request, "comicsdb/partials/arc_issue_items.html", context)
