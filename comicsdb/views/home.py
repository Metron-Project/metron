from datetime import datetime

from django.core.cache import cache
from django.views.generic.base import TemplateView

from comicsdb.models import Issue

# Cache time to live is 30 minutes.
CACHE_TTL = 60 * 30


class HomePageView(TemplateView):
    template_name = "comicsdb/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # time when cached
        update_time = cache.get("home_updated")
        if not update_time:
            update_time = datetime.now()
            cache.set("home_updated", update_time, CACHE_TTL)
        context["updated"] = update_time

        # recently edited issues
        recently_edited = cache.get("recently_edited")
        if not recently_edited:
            recently_edited = (
                Issue.objects.prefetch_related("series", "series__series_type")
                .order_by("-modified")
                .all()[:12]
            )
            cache.set("recently_edited", recently_edited, CACHE_TTL)

        context["recently_edited"] = recently_edited

        return context
