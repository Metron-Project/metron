"""Tests for user_collection signals."""

from issue_ratings.models import IssueRating
from user_collection.models import CollectionItem


def test_setting_collection_rating_creates_issue_rating(collection_user, collection_item):
    """Saving a CollectionItem with a rating creates a matching community IssueRating."""
    assert not IssueRating.objects.filter(
        issue=collection_item.issue, user=collection_user
    ).exists()

    collection_item.rating = 4
    collection_item.save(update_fields=["rating"])

    rating = IssueRating.objects.get(issue=collection_item.issue, user=collection_user)
    assert rating.rating == 4


def test_updating_collection_rating_updates_issue_rating(collection_user, collection_item):
    """Changing an existing collection rating updates the IssueRating rather than duplicating it."""
    collection_item.rating = 2
    collection_item.save(update_fields=["rating"])

    collection_item.rating = 5
    collection_item.save(update_fields=["rating"])

    ratings = IssueRating.objects.filter(issue=collection_item.issue, user=collection_user)
    assert ratings.count() == 1
    assert ratings.first().rating == 5


def test_clearing_collection_rating_deletes_issue_rating(collection_user, collection_item):
    """Clearing a collection rating removes the corresponding IssueRating."""
    collection_item.rating = 3
    collection_item.save(update_fields=["rating"])
    assert IssueRating.objects.filter(issue=collection_item.issue, user=collection_user).exists()

    collection_item.rating = None
    collection_item.save(update_fields=["rating"])

    assert not IssueRating.objects.filter(
        issue=collection_item.issue, user=collection_user
    ).exists()


def test_sync_overwrites_independently_set_issue_rating(collection_user, collection_item):
    """Setting a collection rating overwrites a pre-existing, independently-set community rating."""
    IssueRating.objects.create(issue=collection_item.issue, user=collection_user, rating=1)

    collection_item.rating = 5
    collection_item.save(update_fields=["rating"])

    rating = IssueRating.objects.get(issue=collection_item.issue, user=collection_user)
    assert rating.rating == 5


def test_sync_scoped_to_issue_and_user(collection_user, other_collection_user, collection_issue_1):
    """Syncing only ever touches the (issue, user) pair for the saved collection item."""
    CollectionItem.objects.create(
        user=other_collection_user,
        issue=collection_issue_1,
        quantity=1,
        rating=2,
    )

    ratings = IssueRating.objects.filter(issue=collection_issue_1)
    assert ratings.count() == 1
    assert ratings.get().user == other_collection_user
    assert ratings.get().rating == 2
