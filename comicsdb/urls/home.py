from django.urls import path

from comicsdb.views.home import HomePageView
from comicsdb.views.statistics import statistics

app_name = ""
urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("statistics/", statistics, name="statistics"),
]
