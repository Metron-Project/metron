from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Min
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, FormView

from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from pull_list.forms import AddSeriesToPullListForm
from pull_list.models import PullList, PullListSeries

FOC_WARNING_DAYS = 7
UNDO_SESSION_KEY = "pull_list_undo_series"


def get_or_create_pull_list(user):
    pull_list, _created = PullList.objects.get_or_create(user=user)
    return pull_list


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
        return reverse("pull-list:detail")

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
        active_series = None
        series_param = self.request.GET.get("series")
        if series_param and series_param.isdigit() and int(series_param) in series_ids:
            active_series = next(p.series for p in series_on_list if p.series_id == int(series_param))

        upcoming = Issue.objects.filter(series_id__in=series_ids, store_date__gte=today)
        if active_series:
            upcoming = upcoming.filter(series=active_series)
        upcoming = list(
            upcoming.select_related("series__series_type", "series__publisher").order_by(
                "store_date", "series__sort_name", "number"
            )[:50]
        )
        for issue in upcoming:
            issue.foc_soon = bool(issue.foc_date and today <= issue.foc_date <= foc_limit)
            issue.foc_later = bool(issue.foc_date and issue.foc_date > foc_limit)

        view_mode = "covers" if self.request.GET.get("view") == "covers" else "list"

        # "Undo" after an inline removal (set by RemoveSeriesFromPullListView).
        undo_pk = self.request.session.pop(UNDO_SESSION_KEY, None)

        context.update(
            {
                "pull_list": pull_list,
                "series_on_list": series_on_list,
                "upcoming_issues": upcoming,
                "foc_soon_issues": [i for i in upcoming if i.foc_soon],
                "next_release": upcoming[0].store_date if upcoming else None,
                "active_series": active_series,
                "view_mode": view_mode,
                "undo_series_pk": undo_pk,
                "is_owner": True,
            }
        )
        return context


class RemoveSeriesFromPullListView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """GET shows the confirmation page (no-JS fallback); POST from the list removes directly."""

    model = PullListSeries
    template_name = "pull_list/remove_series_confirm.html"
    success_url = reverse_lazy("pull-list:detail")

    def get_object(self, queryset=None):
        pull_list = get_or_create_pull_list(self.request.user)
        return get_object_or_404(
            PullListSeries,
            pull_list=pull_list,
            series_id=self.kwargs["series_pk"],
        )

    def test_func(self):
        return self.get_object().pull_list.user == self.request.user

    def form_valid(self, form):
        obj = self.get_object()
        series_name = str(obj.series)
        self.request.session[UNDO_SESSION_KEY] = obj.series_id
        result = super().form_valid(form)
        messages.info(
            self.request,
            _("Removed %(series)s from your pull list.") % {"series": series_name},
        )
        return result


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
