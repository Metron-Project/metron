from django.urls import path

from user_collection import views

app_name = "user_collection"

urlpatterns = [
    path("", views.CollectionListView.as_view(), name="list"),
    path("add/", views.CollectionCreateView.as_view(), name="create"),
    path("add-from-series/", views.AddIssuesFromSeriesView.as_view(), name="add-from-series"),
    path("stats/", views.CollectionStatsView.as_view(), name="stats"),
    path("history/", views.ReadingHistoryListView.as_view(), name="history"),
    path("missing/", views.MissingIssuesListView.as_view(), name="missing-list"),
    path(
        "missing/<int:series_id>/",
        views.MissingIssuesDetailView.as_view(),
        name="missing-detail",
    ),
    path("<int:pk>/", views.CollectionDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", views.CollectionUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.CollectionDeleteView.as_view(), name="delete"),
    path("<int:pk>/rate/", views.update_rating, name="rate"),
    path("<int:pk>/read-date/add/", views.add_read_date, name="add_read_date"),
    path(
        "<int:pk>/read-date/<int:read_date_pk>/delete/",
        views.delete_read_date,
        name="delete_read_date",
    ),
]
