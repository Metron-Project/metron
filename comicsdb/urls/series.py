from django.urls import path, re_path

from comicsdb.views.series import (
    SearchSeriesList,
    SeriesCreate,
    SeriesDelete,
    SeriesDetail,
    SeriesIssueList,
    SeriesList,
    SeriesUpdate,
)

app_name = "series"
urlpatterns = [
    path("create/", SeriesCreate.as_view(), name="create"),
    path("", SeriesList.as_view(), name="list"),
    path("<slug:slug>/", SeriesDetail.as_view(), name="detail"),
    path("<slug:slug>/issue_list/", SeriesIssueList.as_view(), name="issue"),
    path("<slug:slug>/update/", SeriesUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", SeriesDelete.as_view(), name="delete"),
    re_path(r"^search/?$", SearchSeriesList.as_view(), name="search"),
]
