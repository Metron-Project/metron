"""Tests for user_collection models."""

from datetime import date
from decimal import Decimal

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

    # Grading tests

    def test_collection_item_grade_default(self, collection_item):
        """Test that grade defaults to None."""
        assert collection_item.grade is None

    def test_collection_item_grading_company_default(self, collection_item):
        """Test that grading_company defaults to empty string."""
        assert collection_item.grading_company == ""

    def test_collection_item_professionally_graded(self, collection_item_professionally_graded):
        """Test creating a professionally graded collection item."""
        item = collection_item_professionally_graded
        assert item.grade == Decimal("9.8")
        assert item.grading_company == CollectionItem.GradingCompany.CGC
        assert item.get_grade_display() == "9.8 (NM/M - Near Mint/Mint)"
        assert item.get_grading_company_display() == "CGC (Certified Guaranty Company)"

    def test_collection_item_user_assessed_grade(self, collection_item_user_graded):
        """Test creating a user-assessed graded collection item."""
        item = collection_item_user_graded
        assert item.grade == Decimal("8.5")
        assert item.grading_company == ""
        assert item.get_grade_display() == "8.5 (VF+ - Very Fine+)"

    def test_collection_item_all_grading_companies(
        self, collection_user, collection_issue_1, create_user
    ):
        """Test all grading company choices."""
        user = create_user()

        # Test CGC
        issue_cgc = Issue.objects.create(
            series=collection_issue_1.series,
            number="301",
            slug="collection-series-301",
            cover_date=date(2024, 1, 1),
            edited_by=user,
            created_by=user,
        )
        item_cgc = CollectionItem.objects.create(
            user=collection_user,
            issue=issue_cgc,
            grade=Decimal("9.4"),
            grading_company=CollectionItem.GradingCompany.CGC,
        )
        assert item_cgc.grading_company == "CGC"

        # Test CBCS
        issue_cbcs = Issue.objects.create(
            series=collection_issue_1.series,
            number="302",
            slug="collection-series-302",
            cover_date=date(2024, 2, 1),
            edited_by=user,
            created_by=user,
        )
        item_cbcs = CollectionItem.objects.create(
            user=collection_user,
            issue=issue_cbcs,
            grade=Decimal("9.2"),
            grading_company=CollectionItem.GradingCompany.CBCS,
        )
        assert item_cbcs.grading_company == "CBCS"

        # Test PGX
        issue_pgx = Issue.objects.create(
            series=collection_issue_1.series,
            number="303",
            slug="collection-series-303",
            cover_date=date(2024, 3, 1),
            edited_by=user,
            created_by=user,
        )
        item_pgx = CollectionItem.objects.create(
            user=collection_user,
            issue=issue_pgx,
            grade=Decimal("9.0"),
            grading_company=CollectionItem.GradingCompany.PGX,
        )
        assert item_pgx.grading_company == "PGX"

    def test_collection_item_grade_choices_valid(
        self, collection_user, collection_issue_1, create_user
    ):
        """Test that valid grade choices are accepted."""
        user = create_user()

        # Test a few key grade values
        test_grades = [
            (Decimal("10.0"), "10.0 (Gem Mint)"),
            (Decimal("9.8"), "9.8 (NM/M - Near Mint/Mint)"),
            (Decimal("9.0"), "9.0 (VF/NM - Very Fine/Near Mint)"),
            (Decimal("8.0"), "8.0 (VF - Very Fine)"),
            (Decimal("5.0"), "5.0 (VG/FN - Very Good/Fine)"),
            (Decimal("1.0"), "1.0 (FR - Fair)"),
            (Decimal("0.5"), "0.5 (PR - Poor)"),
        ]

        for idx, (grade_value, expected_display) in enumerate(test_grades):
            issue = Issue.objects.create(
                series=collection_issue_1.series,
                number=f"400{idx}",
                slug=f"collection-series-400{idx}",
                cover_date=date(2024, 1, idx + 1),
                edited_by=user,
                created_by=user,
            )
            item = CollectionItem.objects.create(
                user=collection_user,
                issue=issue,
                grade=grade_value,
            )
            assert item.grade == grade_value
            assert item.get_grade_display() == expected_display

    def test_collection_item_update_grade(self, collection_item):
        """Test updating grade field."""
        assert collection_item.grade is None
        collection_item.grade = Decimal("9.6")
        collection_item.save()
        collection_item.refresh_from_db()
        assert collection_item.grade == Decimal("9.6")

    def test_collection_item_update_grading_company(self, collection_item_user_graded):
        """Test updating grading_company field."""
        item = collection_item_user_graded
        assert item.grading_company == ""

        # Upgrade to professional grading
        item.grading_company = CollectionItem.GradingCompany.CBCS
        item.save()
        item.refresh_from_db()
        assert item.grading_company == "CBCS"

    def test_collection_item_grade_without_company(
        self, collection_user, collection_issue_1, create_user
    ):
        """Test that grade can exist without grading_company (user-assessed)."""
        user = create_user()
        issue = Issue.objects.create(
            series=collection_issue_1.series,
            number="500",
            slug="collection-series-500",
            cover_date=date(2024, 5, 1),
            edited_by=user,
            created_by=user,
        )

        item = CollectionItem.objects.create(
            user=collection_user,
            issue=issue,
            grade=Decimal("7.5"),
            # grading_company not specified - uses default="" for user-assessed grades
        )
        assert item.grade == Decimal("7.5")
        assert item.grading_company == ""

    def test_collection_item_company_without_grade(
        self, collection_user, collection_issue_1, create_user
    ):
        """Test that grading_company can be set without grade (edge case)."""
        user = create_user()
        issue = Issue.objects.create(
            series=collection_issue_1.series,
            number="501",
            slug="collection-series-501",
            cover_date=date(2024, 6, 1),
            edited_by=user,
            created_by=user,
        )

        # This is technically allowed (no validation prevents it)
        item = CollectionItem.objects.create(
            user=collection_user,
            issue=issue,
            grade=None,
            grading_company=CollectionItem.GradingCompany.CGC,
        )
        assert item.grade is None
        assert item.grading_company == "CGC"
