from django.urls import path, re_path

from comicsdb.views.universe import (
    SearchUniverseList,
    UniverseCharactersLoadMore,
    UniverseCreate,
    UniverseDelete,
    UniverseDetail,
    UniverseDetailRedirect,
    UniverseHistory,
    UniverseIssueList,
    UniverseList,
    UniverseSeriesList,
    UniverseSeriesLoadMore,
    UniverseTeamsLoadMore,
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
    path("<slug:slug>/history/", UniverseHistory.as_view(), name="history"),
    path("<slug:slug>/issue_list/", UniverseIssueList.as_view(), name="issue"),
    path(
        "<slug:slug>/characters/load-more/",
        UniverseCharactersLoadMore.as_view(),
        name="characters-load-more",
    ),
    path(
        "<slug:slug>/teams/load-more/",
        UniverseTeamsLoadMore.as_view(),
        name="teams-load-more",
    ),
    path(
        "<slug:slug>/series/load-more/",
        UniverseSeriesLoadMore.as_view(),
        name="series-load-more",
    ),
    path("<slug:universe>/<slug:series>/", UniverseSeriesList.as_view(), name="series"),
    re_path(r"^search/?$", SearchUniverseList.as_view(), name="search"),
]
