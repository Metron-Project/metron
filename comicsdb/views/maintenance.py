from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views.generic import ListView, TemplateView

from comicsdb.maintenance import CHECKS
from comicsdb.views.constants import PAGINATE_BY


class MaintenanceOverview(LoginRequiredMixin, TemplateView):
    template_name = "comicsdb/maintenance_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Counts are computed live (not cached) so they always match the check pages' totals.
        today = date.today()
        context["checks"] = [(check, check.queryset(today).count()) for check in CHECKS.values()]
        return context


class MaintenanceCheckList(LoginRequiredMixin, ListView):
    template_name = "comicsdb/maintenance_check.html"
    context_object_name = "items"
    paginate_by = PAGINATE_BY

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.maintenance_check = CHECKS[kwargs["check"]]
        except KeyError as exc:
            raise Http404 from exc

    def get_queryset(self):
        return self.maintenance_check.queryset(date.today())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["maintenance_check"] = self.maintenance_check
        return context
