from django.urls import path

from polls.views import PollDeleteView, PollDetailView, PollListView, vote

app_name = "polls"
urlpatterns = [
    path("", PollListView.as_view(), name="list"),
    path("<int:pk>/", PollDetailView.as_view(), name="detail"),
    path("<int:pk>/vote/", vote, name="vote"),
    path("<int:pk>/delete/", PollDeleteView.as_view(), name="delete"),
]
