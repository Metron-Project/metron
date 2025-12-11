"""Tests for user_collection models."""

from datetime import date

import pytest
from django.db import IntegrityError
from djmoney.money import Money

from comicsdb.models.issue import Issue
from user_collection.models import CollectionItem


class TestCollectionItemModel:
    """Tests for the CollectionItem model."""

    def test_collection_item_creation(self, collection_item):
        """Test creating a collection item."""
        assert isinstance(collection_item, CollectionItem)
        assert collection_item.quantity == 1
        assert collection_item.book_format == CollectionItem.BookFormat.PRINT

    def test_collection_item_str(self, collection_item):
        """Test the string representation of a collection item."""
        expected = (
            f"{collection_item.user.username}: {collection_item.issue} "
            f"(x{collection_item.quantity})"
        )
        assert str(collection_item) == expected

    def test_collection_item_with_all_fields(self, collection_item_with_details):
        """Test collection item with all fields populated."""
        item = collection_item_with_details
        assert item.quantity == 2
        assert item.book_format == CollectionItem.BookFormat.BOTH
        assert item.purchase_date == date(2023, 6, 15)
        assert item.purchase_price == Money(4.99, "USD")
        assert item.purchase_store == "Local Comic Shop"
        assert item.storage_location == "Long Box 3"
        assert item.notes == "First printing, signed by artist"

    def test_collection_item_defaults(self, collection_user, collection_issue_1, create_user):
        """Test default values for collection item fields."""
        # Test with a different issue to avoid unique constraint
        user = create_user()
        issue = Issue.objects.create(
            series=collection_issue_1.series,
            number="99",
            slug="collection-series-99",
            cover_date=date(2023, 12, 1),
            edited_by=user,
            created_by=user,
        )
        item = CollectionItem.objects.create(
            user=collection_user,
            issue=issue,
        )
        assert item.quantity == 1
        assert item.book_format == CollectionItem.BookFormat.PRINT
        assert item.purchase_date is None
        assert item.purchase_price is None
        assert item.purchase_store == ""
        assert item.storage_location == ""
        assert item.notes == ""

    def test_collection_item_unique_user_issue(self, collection_user, collection_issue_1):
        """Test that user + issue combination must be unique."""
        CollectionItem.objects.create(
            user=collection_user,
            issue=collection_issue_1,
        )
        # Try to create another item with the same user and issue
        with pytest.raises(IntegrityError):
            CollectionItem.objects.create(
                user=collection_user,
                issue=collection_issue_1,
            )

    def test_collection_item_ordering(
        self, collection_user, collection_issue_1, collection_issue_2, collection_series
    ):
        """Test that items are ordered by user, series sort_name, then cover_date."""
        # Create items in reverse order
        item2 = CollectionItem.objects.create(
            user=collection_user,
            issue=collection_issue_2,
        )
        item1 = CollectionItem.objects.create(
            user=collection_user,
            issue=collection_issue_1,
        )

        items = CollectionItem.objects.filter(user=collection_user)
        assert items.count() == 2
        # Should be ordered by issue__series__sort_name, then issue__cover_date
        assert items[0] == item1  # Issue 1 (earlier cover_date)
        assert items[1] == item2  # Issue 2 (later cover_date)

    def test_collection_item_user_cascade_delete(self, collection_user, collection_item):
        """Test that deleting a user deletes their collection items."""
        user_id = collection_user.id
        assert CollectionItem.objects.filter(user_id=user_id).count() == 1
        collection_user.delete()
        assert CollectionItem.objects.filter(user_id=user_id).count() == 0

    def test_collection_item_issue_cascade_delete(self, collection_issue_1, collection_item):
        """Test that deleting an issue deletes its collection items."""
        issue_id = collection_issue_1.id
        assert CollectionItem.objects.filter(issue_id=issue_id).count() == 1
        collection_issue_1.delete()
        assert CollectionItem.objects.filter(issue_id=issue_id).count() == 0

    def test_collection_item_timestamps(self, collection_item):
        """Test that timestamps are set correctly."""
        assert collection_item.created_on is not None
        assert collection_item.modified is not None

    def test_collection_item_book_format_choices(
        self, collection_user, collection_issue_1, create_user
    ):
        """Test all book format choices."""

        # Create additional issues for testing different formats
        user = create_user()
        issue2 = Issue.objects.create(
            series=collection_issue_1.series,
            number="101",
            slug="collection-series-101",
            cover_date=date(2023, 11, 1),
            edited_by=user,
            created_by=user,
        )
        issue3 = Issue.objects.create(
            series=collection_issue_1.series,
            number="102",
            slug="collection-series-102",
            cover_date=date(2023, 12, 1),
            edited_by=user,
            created_by=user,
        )

        # Test PRINT
        item_print = CollectionItem.objects.create(
            user=collection_user,
            issue=collection_issue_1,
            book_format=CollectionItem.BookFormat.PRINT,
        )
        assert item_print.book_format == "PRINT"

        # Test DIGITAL
        item_digital = CollectionItem.objects.create(
            user=collection_user,
            issue=issue2,
            book_format=CollectionItem.BookFormat.DIGITAL,
        )
        assert item_digital.book_format == "DIGITAL"

        # Test BOTH
        item_both = CollectionItem.objects.create(
            user=collection_user,
            issue=issue3,
            book_format=CollectionItem.BookFormat.BOTH,
        )
        assert item_both.book_format == "BOTH"

    def test_collection_item_multiple_users_same_issue(
        self, collection_user, other_collection_user, collection_issue_1
    ):
        """Test that different users can have the same issue in their collections."""
        item1 = CollectionItem.objects.create(
            user=collection_user,
            issue=collection_issue_1,
        )
        item2 = CollectionItem.objects.create(
            user=other_collection_user,
            issue=collection_issue_1,
        )
        assert item1.user != item2.user
        assert item1.issue == item2.issue

    def test_collection_item_quantity_positive(
        self, collection_user, collection_issue_1, create_user
    ):
        """Test that quantity can be set to various positive values."""

        user = create_user()
        issue = Issue.objects.create(
            series=collection_issue_1.series,
            number="103",
            slug="collection-series-103",
            cover_date=date(2024, 1, 1),
            edited_by=user,
            created_by=user,
        )

        item = CollectionItem.objects.create(
            user=collection_user,
            issue=issue,
            quantity=5,
        )
        assert item.quantity == 5

    def test_collection_item_is_read_default(self, collection_item):
        """Test that is_read defaults to False."""
        assert collection_item.is_read is False

    def test_collection_item_date_read_default(self, collection_item):
        """Test that date_read defaults to None."""
        assert collection_item.date_read is None

    def test_collection_item_with_is_read_true(
        self, collection_user, collection_issue_1, create_user
    ):
        """Test creating a collection item marked as read."""
        user = create_user()
        issue = Issue.objects.create(
            series=collection_issue_1.series,
            number="104",
            slug="collection-series-104",
            cover_date=date(2024, 2, 1),
            edited_by=user,
            created_by=user,
        )

        item = CollectionItem.objects.create(
            user=collection_user,
            issue=issue,
            is_read=True,
        )
        assert item.is_read is True

    def test_collection_item_with_date_read(self, collection_user, collection_issue_1, create_user):
        """Test creating a collection item with a date_read."""
        user = create_user()
        issue = Issue.objects.create(
            series=collection_issue_1.series,
            number="105",
            slug="collection-series-105",
            cover_date=date(2024, 3, 1),
            edited_by=user,
            created_by=user,
        )

        read_date = date(2024, 3, 15)
        item = CollectionItem.objects.create(
            user=collection_user,
            issue=issue,
            is_read=True,
            date_read=read_date,
        )
        assert item.date_read == read_date
        assert item.is_read is True

    def test_collection_item_update_is_read(self, collection_item):
        """Test updating is_read field."""
        assert collection_item.is_read is False
        collection_item.is_read = True
        collection_item.save()
        collection_item.refresh_from_db()
        assert collection_item.is_read is True

    def test_collection_item_update_date_read(self, collection_item):
        """Test updating date_read field."""
        assert collection_item.date_read is None
        read_date = date(2024, 6, 1)
        collection_item.date_read = read_date
        collection_item.save()
        collection_item.refresh_from_db()
        assert collection_item.date_read == read_date

    def test_collection_item_read_status_independent_of_date(
        self, collection_user, collection_issue_1, create_user
    ):
        """Test that is_read can be True without date_read."""
        user = create_user()
        issue = Issue.objects.create(
            series=collection_issue_1.series,
            number="106",
            slug="collection-series-106",
            cover_date=date(2024, 4, 1),
            edited_by=user,
            created_by=user,
        )

        item = CollectionItem.objects.create(
            user=collection_user,
            issue=issue,
            is_read=True,
            date_read=None,
        )
        assert item.is_read is True
        assert item.date_read is None
