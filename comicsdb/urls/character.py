from django.urls import path, re_path

from comicsdb.views.character import (
    CharacterCreate,
    CharacterDelete,
    CharacterDetail,
    CharacterDetailRedirect,
    CharacterHistory,
    CharacterIssueList,
    CharacterList,
    CharacterSeriesList,
    CharacterUpdate,
    SearchCharacterList,
)

app_name = "character"
urlpatterns = [
    path("create/", CharacterCreate.as_view(), name="create"),
    path("", CharacterList.as_view(), name="list"),
    path("<int:pk>/", CharacterDetailRedirect.as_view(), name="redirect"),  # Keep this here
    path("<slug:slug>/", CharacterDetail.as_view(), name="detail"),
    path("<slug:slug>/update/", CharacterUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", CharacterDelete.as_view(), name="delete"),
    path("<slug:slug>/history/", CharacterHistory.as_view(), name="history"),
    path("<slug:slug>/issue_list/", CharacterIssueList.as_view(), name="issue"),
    path("<slug:character>/<slug:series>/", CharacterSeriesList.as_view(), name="series"),
    re_path(r"^search/?$", SearchCharacterList.as_view(), name="search"),
]
