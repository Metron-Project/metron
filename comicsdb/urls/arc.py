from django.urls import path, re_path

from comicsdb.views.arc import (
    ArcCreate,
    ArcDelete,
    ArcDetail,
    ArcDetailRedirect,
    ArcHistory,
    ArcIssueList,
    ArcList,
    ArcUpdate,
    SearchArcList,
)

app_name = "arc"
urlpatterns = [
    path("create/", ArcCreate.as_view(), name="create"),
    path("", ArcList.as_view(), name="list"),
    path("<int:pk>/", ArcDetailRedirect.as_view(), name="redirect"),  # Keep this here
    path("<slug:slug>/", ArcDetail.as_view(), name="detail"),
    path("<slug:slug>/issue_list/", ArcIssueList.as_view(), name="issue"),
    path("<slug:slug>/update/", ArcUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", ArcDelete.as_view(), name="delete"),
    path("<slug:slug>/history/", ArcHistory.as_view(), name="history"),
    re_path(r"^search/?$", SearchArcList.as_view(), name="search"),
]
