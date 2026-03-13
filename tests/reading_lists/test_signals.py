"""Tests for reading_lists signals."""

from datetime import timedelta

from django.utils import timezone

from reading_lists.models import ReadingList, ReadingListItem
from reading_lists.signals import update_reading_list_modified_on_item_change


def test_reading_list_item_save_updates_reading_list_modified(
    reading_list_with_issues, reading_list_item
):
    """Creating or updating a ReadingListItem bumps the parent ReadingList.modified."""
    past = timezone.now() - timedelta(days=1)
    ReadingList.objects.filter(pk=reading_list_with_issues.pk).update(modified=past)
    reading_list_with_issues.refresh_from_db()
    old_modified = reading_list_with_issues.modified

    update_reading_list_modified_on_item_change(sender=ReadingListItem, instance=reading_list_item)
    reading_list_with_issues.refresh_from_db()
    assert reading_list_with_issues.modified > old_modified


def test_reading_list_item_delete_updates_reading_list_modified(
    reading_list_with_issues, reading_list_item
):
    """Deleting a ReadingListItem bumps the parent ReadingList.modified."""
    past = timezone.now() - timedelta(days=1)
    ReadingList.objects.filter(pk=reading_list_with_issues.pk).update(modified=past)
    reading_list_with_issues.refresh_from_db()
    old_modified = reading_list_with_issues.modified

    update_reading_list_modified_on_item_change(sender=ReadingListItem, instance=reading_list_item)
    reading_list_with_issues.refresh_from_db()
    assert reading_list_with_issues.modified > old_modified
