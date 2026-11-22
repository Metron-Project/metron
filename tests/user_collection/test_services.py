"""Tests for user_collection.services."""

from user_collection.models import CollectionItem
from user_collection.services import add_issues_to_collection


def test_add_issues_creates_items_with_format_and_read_flag(
    collection_user, collection_issue_1, collection_issue_2
):
    added, skipped = add_issues_to_collection(
        collection_user,
        [collection_issue_1, collection_issue_2],
        book_format=CollectionItem.BookFormat.DIGITAL,
        mark_as_read=True,
    )

    assert (added, skipped) == (2, 0)
    items = CollectionItem.objects.filter(user=collection_user)
    assert {i.issue_id for i in items} == {collection_issue_1.id, collection_issue_2.id}
    assert all(i.quantity == 1 for i in items)
    assert all(i.book_format == CollectionItem.BookFormat.DIGITAL for i in items)
    assert all(i.is_read for i in items)


def test_add_issues_skips_issues_already_collected(
    collection_user, collection_issue_1, collection_issue_2
):
    existing = CollectionItem.objects.create(
        user=collection_user, issue=collection_issue_1, quantity=3
    )

    added, skipped = add_issues_to_collection(
        collection_user,
        [collection_issue_1, collection_issue_2],
        book_format=CollectionItem.BookFormat.PRINT,
    )

    assert (added, skipped) == (1, 1)
    existing.refresh_from_db()
    assert existing.quantity == 3
    assert CollectionItem.objects.filter(user=collection_user).count() == 2


def test_add_issues_ignores_other_users_collections(
    collection_user, other_collection_user, collection_issue_1
):
    CollectionItem.objects.create(user=other_collection_user, issue=collection_issue_1)

    added, skipped = add_issues_to_collection(
        collection_user, [collection_issue_1], book_format=CollectionItem.BookFormat.PRINT
    )

    assert (added, skipped) == (1, 0)


def test_add_issues_with_nothing_to_add_runs_one_query(
    collection_user, collection_issue_1, django_assert_num_queries
):
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1)

    with django_assert_num_queries(1):
        result = add_issues_to_collection(
            collection_user, [collection_issue_1], book_format=CollectionItem.BookFormat.PRINT
        )

    assert result == (0, 1)
