from django.urls import path, re_path

from reading_lists.views import (
    AddIssuesFromSeriesView,
    AddIssueWithAutocompleteView,
    ReadingListCreateView,
    ReadingListDeleteView,
    ReadingListDetailView,
    ReadingListItemsLoadMore,
    ReadingListListView,
    ReadingListUpdateView,
    RemoveIssueFromReadingListView,
    SearchReadingListListView,
    UserReadingListListView,
)

app_name = "reading-list"
urlpatterns = [
    path("", ReadingListListView.as_view(), name="list"),
    re_path(r"^search/?$", SearchReadingListListView.as_view(), name="search"),
    path("my-lists/", UserReadingListListView.as_view(), name="my-lists"),
    path("create/", ReadingListCreateView.as_view(), name="create"),
    path("<slug:slug>/", ReadingListDetailView.as_view(), name="detail"),
    path("<slug:slug>/update/", ReadingListUpdateView.as_view(), name="update"),
    path("<slug:slug>/delete/", ReadingListDeleteView.as_view(), name="delete"),
    path(
        "<slug:slug>/add-issue/",
        AddIssueWithAutocompleteView.as_view(),
        name="add-issue",
    ),
    path(
        "<slug:slug>/add-from-series/",
        AddIssuesFromSeriesView.as_view(),
        name="add-from-series",
    ),
    path(
        "<slug:slug>/remove-issue/<int:item_pk>/",
        RemoveIssueFromReadingListView.as_view(),
        name="remove-issue",
    ),
    path(
        "<slug:slug>/items-load-more/",
        ReadingListItemsLoadMore.as_view(),
        name="items-load-more",
    ),
]
