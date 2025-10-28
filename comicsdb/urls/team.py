from django.urls import path, re_path

from comicsdb.views.team import (
    SearchTeamList,
    TeamCreate,
    TeamDelete,
    TeamDetail,
    TeamDetailRedirect,
    TeamHistory,
    TeamIssueList,
    TeamList,
    TeamUpdate,
)

app_name = "team"
urlpatterns = [
    path("create/", TeamCreate.as_view(), name="create"),
    path("", TeamList.as_view(), name="list"),
    path("<int:pk>/", TeamDetailRedirect.as_view(), name="redirect"),  # Keep this here
    path("<slug:slug>/", TeamDetail.as_view(), name="detail"),
    path("<slug:slug>/update/", TeamUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", TeamDelete.as_view(), name="delete"),
    path("<slug:slug>/history/", TeamHistory.as_view(), name="history"),
    path("<slug:slug>/issue_list/", TeamIssueList.as_view(), name="issue"),
    re_path(r"^search/?$", SearchTeamList.as_view(), name="search"),
]
