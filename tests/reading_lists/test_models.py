"""Tests for reading_lists models."""

import pytest
from django.db import IntegrityError

from reading_lists.models import ReadingList, ReadingListItem

HTTP_200_OK = 200


class TestReadingListModel:
    """Tests for the ReadingList model."""

    def test_reading_list_creation(self, public_reading_list):
        """Test creating a reading list."""
        assert isinstance(public_reading_list, ReadingList)
        assert public_reading_list.name == "Public Reading List"
        assert public_reading_list.desc == "A public reading list for testing"
        assert not public_reading_list.is_private

    def test_reading_list_str(self, public_reading_list):
        """Test the string representation of a reading list."""
        expected = f"{public_reading_list.user.username}: {public_reading_list.name}"
        assert str(public_reading_list) == expected

    def test_reading_list_absolute_url(self, client, public_reading_list):
        """Test the get_absolute_url method."""
        resp = client.get(public_reading_list.get_absolute_url())
        assert resp.status_code == HTTP_200_OK

    def test_reading_list_slug_generation(self, public_reading_list):
        """Test that slug is automatically generated."""
        assert public_reading_list.slug == "public-reading-list"

    def test_reading_list_unique_user_name(self, reading_list_user):
        """Test that user + name combination must be unique."""
        ReadingList.objects.create(
            user=reading_list_user,
            name="Test List",
        )
        # Try to create another list with the same user and name
        with pytest.raises(IntegrityError):
            ReadingList.objects.create(
                user=reading_list_user,
                name="Test List",
            )

    def test_reading_list_ordering(self, reading_list_user, other_user):
        """Test that reading lists are ordered by user, then name."""
        list1 = ReadingList.objects.create(
            user=reading_list_user,
            name="Z List",
        )
        list2 = ReadingList.objects.create(
            user=reading_list_user,
            name="A List",
        )
        list3 = ReadingList.objects.create(
            user=other_user,
            name="B List",
        )

        lists = ReadingList.objects.all()
        # Should be ordered by user first (alphabetically by username), then name
        # "other_user" comes after "readinglist_user" alphabetically
        assert lists[0] == list2  # readinglist_user: A List
        assert lists[1] == list1  # readinglist_user: Z List
        assert lists[2] == list3  # other_user: B List

    def test_reading_list_attribution_source(self, reading_list_with_issues):
        """Test attribution source field."""
        assert reading_list_with_issues.attribution_source == ReadingList.AttributionSource.CBRO
        assert reading_list_with_issues.attribution_url == "https://example.com/reading-order"

    def test_reading_list_start_year(self, reading_list_with_issues):
        """Test the start_year property."""
        assert reading_list_with_issues.start_year == 2020

    def test_reading_list_start_year_empty(self, public_reading_list):
        """Test the start_year property with no issues."""
        assert public_reading_list.start_year is None

    def test_reading_list_end_year(self, reading_list_with_issues):
        """Test the end_year property."""
        assert reading_list_with_issues.end_year == 2020

    def test_reading_list_end_year_empty(self, public_reading_list):
        """Test the end_year property with no issues."""
        assert public_reading_list.end_year is None

    def test_reading_list_publishers(self, reading_list_with_issues, reading_list_publisher):
        """Test the publishers property."""
        publishers = reading_list_with_issues.publishers
        assert publishers.count() == 1
        assert publishers.first() == reading_list_publisher

    def test_reading_list_publishers_empty(self, public_reading_list):
        """Test the publishers property with no issues."""
        assert public_reading_list.publishers.count() == 0


class TestReadingListItemModel:
    """Tests for the ReadingListItem model."""

    def test_reading_list_item_creation(self, reading_list_item):
        """Test creating a reading list item."""
        assert isinstance(reading_list_item, ReadingListItem)
        assert reading_list_item.order == 1

    def test_reading_list_item_str(self, reading_list_item):
        """Test the string representation of a reading list item."""
        expected = (
            f"{reading_list_item.reading_list.name} - {reading_list_item.issue} "
            f"(Order: {reading_list_item.order})"
        )
        assert str(reading_list_item) == expected

    def test_reading_list_item_unique_reading_list_issue(
        self, reading_list_with_issues, reading_list_issue_1
    ):
        """Test that reading_list + issue combination must be unique."""
        # Try to add the same issue again
        with pytest.raises(IntegrityError):
            ReadingListItem.objects.create(
                reading_list=reading_list_with_issues,
                issue=reading_list_issue_1,
                order=10,
            )

    def test_reading_list_item_ordering(self, reading_list_with_issues):
        """Test that items are ordered by reading_list, then order."""
        items = reading_list_with_issues.reading_list_items.all()
        assert items.count() == 3
        assert items[0].order == 1
        assert items[1].order == 2
        assert items[2].order == 3

    def test_reading_list_cascade_delete(
        self, reading_list_with_issues, reading_list_issue_1, reading_list_issue_2
    ):
        """Test that deleting a reading list deletes its items."""
        list_id = reading_list_with_issues.id
        assert ReadingListItem.objects.filter(reading_list_id=list_id).count() == 3
        reading_list_with_issues.delete()
        assert ReadingListItem.objects.filter(reading_list_id=list_id).count() == 0

    def test_issue_cascade_delete(self, reading_list_with_issues, reading_list_issue_1):
        """Test that deleting an issue deletes its reading list items."""
        issue_id = reading_list_issue_1.id
        assert ReadingListItem.objects.filter(issue_id=issue_id).count() == 1
        reading_list_issue_1.delete()
        assert ReadingListItem.objects.filter(issue_id=issue_id).count() == 0
        # Reading list should still exist
        assert ReadingList.objects.filter(id=reading_list_with_issues.id).exists()

    def test_reading_list_item_default_order(self, public_reading_list, reading_list_issue_1):
        """Test that order defaults to 0."""
        item = ReadingListItem.objects.create(
            reading_list=public_reading_list,
            issue=reading_list_issue_1,
        )
        assert item.order == 0
