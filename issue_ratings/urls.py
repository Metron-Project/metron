from django.urls import path

from issue_ratings.views import update_issue_rating

app_name = "issue-ratings"

urlpatterns = [
    path("<int:pk>/rate/", update_issue_rating, name="rate"),
]
