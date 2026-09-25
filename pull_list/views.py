from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Min
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, FormView

from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from pull_list.forms import AddSeriesToPullListForm
from pull_list.models import PullList, PullListSeries

FOC_WARNING_DAYS = 7
UPCOMING_LIMIT = 50
UNDO_SESSION_KEY = "pull_list_undo_series"


def get_or_create_pull_list(user):
    pull_list, _created = PullList.objects.get_or_create(user=user)
    # Reuse the user we already have, so pull_list.user (e.g. in __str__) doesn't re-query it.
    pull_list.user = user
    return pull_list


def detail_query(params, drop_series_pk=None) -> str:
    """Rebuild the detail page's ?view=/?series= state from ``params`` (e.g. request.GET).

    Returns "" or a string starting with "?", so it can be appended to a URL. The series
    filter is dropped when it points at ``drop_series_pk`` (the series being removed).
    """
    query = {}
    if params.get("view") == "covers":
        query["view"] = "covers"
    series = params.get("series", "")
    if series.isdigit() and int(series) != drop_series_pk:
        query["series"] = series
    return f"?{urlencode(query)}" if query else ""


class PullListDetailView(LoginRequiredMixin, FormView):
    template_name = "pull_list/pulllist_detail.html"
    form_class = AddSeriesToPullListForm

    def get_pull_list(self):
        if not hasattr(self, "_pull_list"):
            self._pull_list = get_or_create_pull_list(self.request.user)
        return self._pull_list

    def form_valid(self, form):
        pull_list = self.get_pull_list()
        series = form.cleaned_data["series"]
        _obj, created = PullListSeries.objects.get_or_create(pull_list=pull_list, series=series)
        # HTMX posts (the Undo button) only swap #pull-list-content, which doesn't include
        # the messages area, so a message would be consumed without being shown.
        if not self.request.htmx:
            if created:
                messages.success(
                    self.request, _("Added %(series)s to your pull list.") % {"series": series}
                )
            else:
                messages.info(
                    self.request,
                    _("%(series)s is already on your pull list.") % {"series": series},
                )
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("pull-list:detail") + detail_query(self.request.GET)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pull_list = self.get_pull_list()
        today = timezone.localdate()
        foc_limit = today + timedelta(days=FOC_WARNING_DAYS)

        series_on_list = list(
            pull_list.pull_list_series.select_related(
                "series__series_type", "series__publisher"
            ).order_by("series__sort_name")
        )
        series_ids = [pls.series_id for pls in series_on_list]

        # Next store date per series, for the sidebar.
        next_dates = dict(
            Issue.objects.filter(series_id__in=series_ids, store_date__gte=today)
            .values("series_id")
            .annotate(next_store_date=Min("store_date"))
            .values_list("series_id", "next_store_date")
        )
        for pls in series_on_list:
            pls.next_store_date = next_dates.get(pls.series_id)

        # Optional ?series=<pk> filter from the sidebar.
        series_by_pk = {pls.series_id: pls.series for pls in series_on_list}
        series_param = self.request.GET.get("series", "")
        active_series = series_by_pk.get(int(series_param)) if series_param.isdigit() else None

        # Header summary and FOC banner cover the whole list, regardless of the filter,
        # so a filter never hides an order deadline.
        all_upcoming = Issue.objects.filter(series_id__in=series_ids, store_date__gte=today)
        shown = all_upcoming.filter(series=active_series) if active_series else all_upcoming
        upcoming = list(
            shown.select_related("series__series_type", "series__publisher").order_by(
                "store_date", "series__sort_name", "number"
            )[:UPCOMING_LIMIT]
        )
        for issue in upcoming:
            issue.foc_soon = bool(issue.foc_date and today <= issue.foc_date <= foc_limit)
            issue.foc_later = bool(issue.foc_date and issue.foc_date > foc_limit)

        if not active_series and len(upcoming) < UPCOMING_LIMIT:
            # Common case: the loaded list is every upcoming issue, so reuse it.
            upcoming_count = shown_count = len(upcoming)
            foc_soon_issues = sorted(
                (i for i in upcoming if i.foc_soon),
                key=lambda i: (i.foc_date, i.series.sort_name, i.number),
            )
        else:
            upcoming_count = all_upcoming.count()
            shown_count = shown.count() if active_series else upcoming_count
            foc_soon_issues = list(
                all_upcoming.filter(foc_date__gte=today, foc_date__lte=foc_limit)
                .select_related("series__series_type")
                .order_by("foc_date", "series__sort_name", "number")
            )

        view_mode = "covers" if self.request.GET.get("view") == "covers" else "list"

        # "Undo" after an inline removal (set by RemoveSeriesFromPullListView).
        undo_series = self.request.session.pop(UNDO_SESSION_KEY, None)
        if not isinstance(undo_series, dict):
            undo_series = None

        context.update(
            {
                "pull_list": pull_list,
                "series_on_list": series_on_list,
                "upcoming_issues": upcoming,
                "upcoming_count": upcoming_count,
                "shown_count": shown_count,
                "foc_soon_issues": foc_soon_issues,
                "next_release": min(next_dates.values(), default=None),
                "active_series": active_series,
                "view_mode": view_mode,
                "filter_query": detail_query(
                    {"view": view_mode, "series": str(active_series.pk) if active_series else ""}
                ),
                "undo_series": undo_series,
                "today": today,
            }
        )
        return context


class RemoveSeriesFromPullListView(LoginRequiredMixin, DeleteView):
    """GET shows the confirmation page (no-JS fallback); POST from the list removes directly.

    Only the user's own pull list is searched, so another user's entry is a 404.
    """

    model = PullListSeries
    template_name = "pull_list/remove_series_confirm.html"

    def get_object(self, queryset=None):
        if not hasattr(self, "_object"):
            self._object = get_object_or_404(
                PullListSeries.objects.select_related("series"),
                pull_list__user=self.request.user,
                series_id=self.kwargs["series_pk"],
            )
        return self._object

    def get_success_url(self):
        # Keep the page's filter/view, unless the filter was the series being removed.
        return reverse("pull-list:detail") + detail_query(
            self.request.GET, drop_series_pk=self.object.series_id
        )

    def form_valid(self, form):
        # The detail page's Undo notification names the series, so no separate message.
        self.request.session[UNDO_SESSION_KEY] = {
            "pk": self.object.series_id,
            "name": str(self.object.series),
        }
        return super().form_valid(form)


@login_required
@require_POST
def toggle_pull_list_series(request, slug):
    series = get_object_or_404(Series, slug=slug)
    pull_list, _created = PullList.objects.get_or_create(user=request.user)
    pull_list_series, created = PullListSeries.objects.get_or_create(
        pull_list=pull_list, series=series
    )
    if not created:
        pull_list_series.delete()
        on_pull_list = False
    else:
        on_pull_list = True
    return render(
        request,
        "pull_list/partials/pull_list_button.html",
        {"series": series, "on_pull_list": on_pull_list},
    )
