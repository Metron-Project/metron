from django.urls import path, re_path

from comicsdb.views.universe import (
    SearchUniverseList,
    UniverseCreate,
    UniverseDelete,
    UniverseDetail,
    UniverseDetailRedirect,
    UniverseIssueList,
    UniverseList,
    UniverseSeriesList,
    UniverseUpdate,
)

app_name = "universe"
urlpatterns = [
    path("create/", UniverseCreate.as_view(), name="create"),
    path("", UniverseList.as_view(), name="list"),
    path("<int:pk>/", UniverseDetailRedirect.as_view(), name="redirect"),  # Keep this here
    path("<slug:slug>/", UniverseDetail.as_view(), name="detail"),
    path("<slug:slug>/update/", UniverseUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", UniverseDelete.as_view(), name="delete"),
    path("<slug:slug>/issue_list/", UniverseIssueList.as_view(), name="issue"),
    path("<slug:universe>/<slug:series>/", UniverseSeriesList.as_view(), name="series"),
    re_path(r"^search/?$", SearchUniverseList.as_view(), name="search"),
]
