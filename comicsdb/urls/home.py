from django.urls import path

from comicsdb.views.home import HomePageView, recently_edited_issues
from comicsdb.views.statistics import statistics, statistics_charts, statistics_totals

app_name = ""
urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("statistics/", statistics, name="statistics"),
    path("statistics/totals/", statistics_totals, name="statistics-totals"),
    path("statistics/charts/", statistics_charts, name="statistics-charts"),
    path("recently-edited/", recently_edited_issues, name="recently-edited"),
]
