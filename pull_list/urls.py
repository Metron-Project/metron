from django.urls import path

from pull_list.views import (
    PullListDetailView,
    RemoveSeriesFromPullListView,
    toggle_pull_list_series,
)

app_name = "pull-list"

urlpatterns = [
    path("", PullListDetailView.as_view(), name="detail"),
    path("remove/<int:series_pk>/", RemoveSeriesFromPullListView.as_view(), name="remove-series"),
    path("toggle/<slug:slug>/", toggle_pull_list_series, name="toggle"),
]
