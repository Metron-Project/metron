from django.urls import path, re_path

from comicsdb.views.publisher import (
    PublisherCreate,
    PublisherDelete,
    PublisherDetail,
    PublisherDetailRedirect,
    PublisherHistory,
    PublisherImprintsLoadMore,
    PublisherList,
    PublisherSeriesList,
    PublisherUniversesLoadMore,
    PublisherUpdate,
    SearchPublisherList,
)

app_name = "publisher"
urlpatterns = [
    path("create/", PublisherCreate.as_view(), name="create"),
    path("", PublisherList.as_view(), name="list"),
    path("<int:pk>/", PublisherDetailRedirect.as_view(), name="redirect"),  # Keep this here
    path("<slug:slug>/", PublisherDetail.as_view(), name="detail"),
    path("<slug:slug>/series_list/", PublisherSeriesList.as_view(), name="series"),
    path("<slug:slug>/update/", PublisherUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", PublisherDelete.as_view(), name="delete"),
    path("<slug:slug>/history/", PublisherHistory.as_view(), name="history"),
    path(
        "<slug:slug>/imprints/load-more/",
        PublisherImprintsLoadMore.as_view(),
        name="imprints-load-more",
    ),
    path(
        "<slug:slug>/universes/load-more/",
        PublisherUniversesLoadMore.as_view(),
        name="universes-load-more",
    ),
    re_path(r"^search/?$", SearchPublisherList.as_view(), name="search"),
]
