"""Tests for reading_lists models."""

import pytest
from django.core.exceptions import ValidationError
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

    def test_reading_list_str_with_attribution(self, reading_list_with_issues):
        """Test the string representation of a reading list with attribution source."""
        expected = (
            f"{reading_list_with_issues.user.username}: {reading_list_with_issues.name} "
            f"({reading_list_with_issues.get_attribution_source_display()})"
        )
        assert str(reading_list_with_issues) == expected

    def test_reading_list_absolute_url(self, client, public_reading_list):
        """Test the get_absolute_url method."""
        resp = client.get(public_reading_list.get_absolute_url())
        assert resp.status_code == HTTP_200_OK

    def test_reading_list_slug_generation(self, public_reading_list):
        """Test that slug is automatically generated."""
        assert public_reading_list.slug == "public-reading-list"

    def test_reading_list_list_type_default(self, public_reading_list):
        """Test that list_type defaults to Event."""
        assert public_reading_list.list_type == ReadingList.ListType.EVENT

    def test_reading_list_list_type_display(self, public_reading_list):
        """Test get_list_type_display returns the human-readable label."""
        assert public_reading_list.get_list_type_display() == "Event"

    def test_reading_list_list_type_choices(self, reading_list_user):
        """Test that all ListType choices can be assigned and saved."""
        for value, label in ReadingList.ListType.choices:
            rl = ReadingList.objects.create(
                user=reading_list_user,
                name=f"List {value}",
                list_type=value,
            )
            assert rl.list_type == value
            assert rl.get_list_type_display() == label

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
        """Test that reading lists are ordered by name, attribution_source, then user."""
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
        # Should be ordered by name first, then attribution_source (all blank), then user
        assert lists[0] == list2  # A List (readinglist_user)
        assert lists[1] == list3  # B List (other_user)
        assert lists[2] == list1  # Z List (readinglist_user)

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

    def test_reading_list_previous_next_default_none(self, public_reading_list):
        """Test that previous and next default to None."""
        assert public_reading_list.previous is None
        assert public_reading_list.next is None

    def test_reading_list_previous_next_assignment(self, reading_list_user):
        """Test that previous and next can be linked to other reading lists."""
        first = ReadingList.objects.create(user=reading_list_user, name="Part One")
        second = ReadingList.objects.create(user=reading_list_user, name="Part Two", previous=first)
        first.next = second
        first.save()

        assert second.previous == first
        assert first.next == second

    def test_reading_list_next_set_null_on_delete(self, reading_list_user):
        """Test that next is set to null when the linked reading list is deleted."""
        first = ReadingList.objects.create(user=reading_list_user, name="Part One")
        second = ReadingList.objects.create(user=reading_list_user, name="Part Two", previous=first)
        first.next = second
        first.save()

        second.delete()
        first.refresh_from_db()
        assert first.next is None

    def test_reading_list_clean_rejects_self_as_previous(self, public_reading_list):
        """Test that a reading list cannot be its own previous list."""
        public_reading_list.previous = public_reading_list
        with pytest.raises(ValidationError):
            public_reading_list.clean()

    def test_reading_list_clean_rejects_self_as_next(self, public_reading_list):
        """Test that a reading list cannot be its own next list."""
        public_reading_list.next = public_reading_list
        with pytest.raises(ValidationError):
            public_reading_list.clean()

    def test_reading_list_clean_rejects_same_previous_and_next(self, reading_list_user):
        """Test that previous and next cannot both point to the same reading list."""
        other = ReadingList.objects.create(user=reading_list_user, name="Other List")
        reading_list = ReadingList.objects.create(
            user=reading_list_user, name="Test List", previous=other, next=other
        )
        with pytest.raises(ValidationError):
            reading_list.clean()

    def test_reading_list_clean_allows_valid_previous_and_next(self, reading_list_user):
        """Test that clean() passes when previous and next are distinct lists."""
        before = ReadingList.objects.create(user=reading_list_user, name="Before")
        after = ReadingList.objects.create(user=reading_list_user, name="After")
        middle = ReadingList.objects.create(
            user=reading_list_user, name="Middle", previous=before, next=after
        )
        middle.clean()

    def test_reading_list_setting_next_syncs_reverse_previous(self, reading_list_user):
        """Test that setting A.next = B also sets B.previous = A."""
        first = ReadingList.objects.create(user=reading_list_user, name="Part One")
        second = ReadingList.objects.create(user=reading_list_user, name="Part Two")

        first.next = second
        first.save()

        second.refresh_from_db()
        assert second.previous == first

    def test_reading_list_setting_previous_syncs_reverse_next(self, reading_list_user):
        """Test that setting B.previous = A also sets A.next = B."""
        first = ReadingList.objects.create(user=reading_list_user, name="Part One")
        second = ReadingList.objects.create(user=reading_list_user, name="Part Two")

        second.previous = first
        second.save()

        first.refresh_from_db()
        assert first.next == second

    def test_reading_list_setting_next_at_creation_syncs_reverse_previous(self, reading_list_user):
        """Test that the reverse link is synced when next is set at creation time."""
        first = ReadingList.objects.create(user=reading_list_user, name="Part One")
        second = ReadingList.objects.create(user=reading_list_user, name="Part Two", previous=first)

        first.refresh_from_db()
        assert first.next == second

    def test_reading_list_clearing_next_clears_reverse_previous(self, reading_list_user):
        """Test that clearing A.next also clears B.previous."""
        first = ReadingList.objects.create(user=reading_list_user, name="Part One")
        second = ReadingList.objects.create(user=reading_list_user, name="Part Two")
        first.next = second
        first.save()

        first.next = None
        first.save()

        second.refresh_from_db()
        assert second.previous is None

    def test_reading_list_reassigning_next_clears_old_reverse_previous(self, reading_list_user):
        """Test that changing A.next from B to C clears B.previous and sets C.previous."""
        first = ReadingList.objects.create(user=reading_list_user, name="Part One")
        second = ReadingList.objects.create(user=reading_list_user, name="Part Two")
        third = ReadingList.objects.create(user=reading_list_user, name="Part Three")
        first.next = second
        first.save()

        first.next = third
        first.save()

        second.refresh_from_db()
        third.refresh_from_db()
        assert second.previous is None
        assert third.previous == first

    def test_reading_list_unrelated_save_does_not_disturb_links(self, reading_list_user):
        """Test that saving unrelated field changes doesn't clear existing links."""
        first = ReadingList.objects.create(user=reading_list_user, name="Part One")
        second = ReadingList.objects.create(user=reading_list_user, name="Part Two")
        first.next = second
        first.save()

        first.desc = "Updated description"
        first.save()

        second.refresh_from_db()
        assert second.previous == first


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
        """Test that order defaults to 1."""
        item = ReadingListItem.objects.create(
            reading_list=public_reading_list,
            issue=reading_list_issue_1,
        )
        assert item.order == 1
