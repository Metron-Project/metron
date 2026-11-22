"""Reading list views, split by area. Re-exported here for reading_lists/urls.py."""

from reading_lists.views.detail import ReadingListDetailView, ReadingListItemsLoadMore
from reading_lists.views.edit import (
    AssignReadingListToMetronView,
    ReadingListCreateView,
    ReadingListDeleteView,
    ReadingListUpdateView,
)
from reading_lists.views.inline import (
    cancel_edit_issue_type,
    edit_issue_type,
    update_issue_type,
    update_reading_list_rating,
)
from reading_lists.views.items import (
    AddIssuesFromArcView,
    AddIssuesFromSeriesView,
    AddIssueWithAutocompleteView,
    RemoveIssueFromReadingListView,
)
from reading_lists.views.lists import (
    ReadingListListView,
    SearchReadingListListView,
    UserReadingListListView,
)

__all__ = [
    "AddIssueWithAutocompleteView",
    "AddIssuesFromArcView",
    "AddIssuesFromSeriesView",
    "AssignReadingListToMetronView",
    "ReadingListCreateView",
    "ReadingListDeleteView",
    "ReadingListDetailView",
    "ReadingListItemsLoadMore",
    "ReadingListListView",
    "ReadingListUpdateView",
    "RemoveIssueFromReadingListView",
    "SearchReadingListListView",
    "UserReadingListListView",
    "cancel_edit_issue_type",
    "edit_issue_type",
    "update_issue_type",
    "update_reading_list_rating",
]
