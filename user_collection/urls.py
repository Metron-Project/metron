from django.urls import path

from user_collection import views

app_name = "user_collection"

urlpatterns = [
    path("", views.CollectionListView.as_view(), name="list"),
    path("add/", views.CollectionCreateView.as_view(), name="create"),
    path("add-from-series/", views.AddIssuesFromSeriesView.as_view(), name="add-from-series"),
    path("stats/", views.CollectionStatsView.as_view(), name="stats"),
    path("<int:pk>/", views.CollectionDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", views.CollectionUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", views.CollectionDeleteView.as_view(), name="delete"),
]
