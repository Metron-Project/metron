from django.apps import apps
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.views import View

APP_NAME = "timeline"


class TimelineView(View):
    def get(self, request) -> HttpResponse:
        app = apps.get_app_config(APP_NAME)
        return render(request, "timeline.html", {"entries": app.entries})


class TimelineEntryRevealView(View):
    def get(self, request, slug: str) -> HttpResponse:
        app = apps.get_app_config(APP_NAME)
        entry = next((e for e in app.entries if e["slug"] == slug), None)
        if entry is None:
            return HttpResponseNotFound()
        return render(request, "timeline_entry.html", {"entry": entry, "revealed": True})
