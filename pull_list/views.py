from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import DeleteView, FormView

from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from pull_list.forms import AddSeriesToPullListForm
from pull_list.models import PullList, PullListSeries


def get_or_create_pull_list(user):
    pull_list, _ = PullList.objects.get_or_create(user=user)
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
        _, created = PullListSeries.objects.get_or_create(pull_list=pull_list, series=series)
        if created:
            messages.success(self.request, f"Added {series} to your pull list.")
        else:
            messages.info(self.request, f"{series} is already on your pull list.")
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("pull-list:detail")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pull_list = self.get_pull_list()
        context["pull_list"] = pull_list
        context["series_on_list"] = pull_list.pull_list_series.select_related(
            "series__series_type",
            "series__publisher",
        ).order_by("series__sort_name")
        today = timezone.now().date()
        series_ids = list(pull_list.pull_list_series.values_list("series_id", flat=True))
        context["upcoming_issues"] = (
            Issue.objects.filter(series_id__in=series_ids, store_date__gte=today)
            .select_related("series__series_type", "series__publisher")
            .order_by("store_date", "series__sort_name")[:50]
        )
        context["is_owner"] = True
        return context


class RemoveSeriesFromPullListView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
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
        series_name = str(self.get_object().series)
        result = super().form_valid(form)
        messages.success(self.request, f"Removed {series_name} from your pull list.")
        return result


@login_required
@require_POST
def toggle_pull_list_series(request, slug):
    series = get_object_or_404(Series, slug=slug)
    pull_list, _ = PullList.objects.get_or_create(user=request.user)
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
