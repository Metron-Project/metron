from django.urls import path

from timeline.views import TimelineEntryRevealView, TimelineView

app_name = "timeline"
urlpatterns = [
    path("", TimelineView.as_view(), name="timeline"),
    path("reveal/<slug:slug>/", TimelineEntryRevealView.as_view(), name="reveal"),
]
