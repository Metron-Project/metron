from django.urls import path, re_path

from comicsdb.views.issue import (
    CreatorAutocomplete,
    FutureList,
    IssueCreate,
    IssueDelete,
    IssueDetail,
    IssueDetailRedirect,
    IssueList,
    IssueUpdate,
    NextWeekList,
    SearchIssueList,
    SeriesAutocomplete,
    WeekList,
)

app_name = "issue"
urlpatterns = [
    path("create/", IssueCreate.as_view(), name="create"),
    path("", IssueList.as_view(), name="list"),
    path("<int:pk>/", IssueDetailRedirect.as_view(), name="redirect"),  # Keep this here
    path("<slug:slug>/", IssueDetail.as_view(), name="detail"),
    path("<slug:slug>/update/", IssueUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", IssueDelete.as_view(), name="delete"),
    path("thisweek", WeekList.as_view(), name="thisweek"),
    path("nextweek", NextWeekList.as_view(), name="nextweek"),
    path("future", FutureList.as_view(), name="future"),
    re_path(
        r"^creator-autocomplete/?$",
        CreatorAutocomplete.as_view(),
        name="creator-autocomplete",
    ),
    re_path(
        r"^series-autocomplete/?$",
        SeriesAutocomplete.as_view(),
        name="series-autocomplete",
    ),
    re_path(r"^search/?$", SearchIssueList.as_view(), name="search"),
]
