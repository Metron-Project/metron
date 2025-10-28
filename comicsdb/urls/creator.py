from django.urls import path, re_path

from comicsdb.views.creator import (
    CreatorCreate,
    CreatorDelete,
    CreatorDetail,
    CreatorDetailRedirect,
    CreatorHistory,
    CreatorIssueList,
    CreatorList,
    CreatorSeriesList,
    CreatorUpdate,
    SearchCreatorList,
)

app_name = "creator"
urlpatterns = [
    path("create/", CreatorCreate.as_view(), name="create"),
    path("", CreatorList.as_view(), name="list"),
    path("<int:pk>/", CreatorDetailRedirect.as_view(), name="redirect"),  # Keep this here
    path("<slug:slug>/", CreatorDetail.as_view(), name="detail"),
    path("<slug:slug>/update/", CreatorUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", CreatorDelete.as_view(), name="delete"),
    path("<slug:slug>/history/", CreatorHistory.as_view(), name="history"),
    path("<slug:slug>/issue_list/", CreatorIssueList.as_view(), name="issue"),
    path("<slug:creator>/<slug:series>/", CreatorSeriesList.as_view(), name="series"),
    re_path(r"^search/?$", SearchCreatorList.as_view(), name="search"),
]
