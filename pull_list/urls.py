from django.urls import path

from pull_list.views import (
    PublicPullListDetailView,
    PullListDetailView,
    PullListSettingsView,
    RemoveSeriesFromPullListView,
)

app_name = "pull-list"

urlpatterns = [
    path("", PullListDetailView.as_view(), name="detail"),
    path("settings/", PullListSettingsView.as_view(), name="settings"),
    path("remove/<int:series_pk>/", RemoveSeriesFromPullListView.as_view(), name="remove-series"),
    path("<int:pk>/", PublicPullListDetailView.as_view(), name="public-detail"),
]
