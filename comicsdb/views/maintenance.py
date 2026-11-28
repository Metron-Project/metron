from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import Http404
from django.views.generic import ListView, TemplateView

from comicsdb.maintenance import CHECKS, MaintenanceCheck
from comicsdb.views.constants import PAGINATE_BY

# Cache time to live is 30 minutes.
CACHE_TTL = 60 * 30


def check_count(check: MaintenanceCheck) -> int:
    key = f"maintenance_count_{check.slug}"
    count = cache.get(key)
    if count is None:
        count = check.queryset(date.today()).count()
        cache.set(key, count, CACHE_TTL)
    return count


class MaintenanceOverview(LoginRequiredMixin, TemplateView):
    template_name = "comicsdb/maintenance_overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["checks"] = [(check, check_count(check)) for check in CHECKS.values()]
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
