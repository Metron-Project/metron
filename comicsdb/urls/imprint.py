from django.urls import path, re_path

from comicsdb.views.imprint import (
    ImprintCreate,
    ImprintDelete,
    ImprintDetail,
    ImprintDetailRedirect,
    ImprintList,
    ImprintSeriesList,
    ImprintUpdate,
    SearchImprintList,
)

app_name = "imprint"
urlpatterns = [
    path("create/", ImprintCreate.as_view(), name="create"),
    path("", ImprintList.as_view(), name="list"),
    path("<int:pk>/", ImprintDetailRedirect.as_view(), name="redirect"),  # Keep this here
    path("<slug:slug>/", ImprintDetail.as_view(), name="detail"),
    path("<slug:slug>/series_list/", ImprintSeriesList.as_view(), name="series"),
    path("<slug:slug>/update/", ImprintUpdate.as_view(), name="update"),
    path("<slug:slug>/delete/", ImprintDelete.as_view(), name="delete"),
    re_path(r"^search/?$", SearchImprintList.as_view(), name="search"),
]
