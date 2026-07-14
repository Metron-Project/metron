"""Tests for the backfill_issue_ratings management command."""

import io

from django.core.management import call_command
from django.db.models.signals import post_save

from issue_ratings.models import IssueRating
from user_collection.models import CollectionItem
from user_collection.signals import sync_issue_rating_from_collection_item


def create_legacy_rated_item(**kwargs):
    """Create a CollectionItem with a rating without the sync signal firing.

    Simulates data that predates the user_collection -> issue_ratings sync feature.
    """
    post_save.disconnect(
        sync_issue_rating_from_collection_item,
        sender=CollectionItem,
        dispatch_uid="post_save_sync_issue_rating_from_collection_item",
    )
    try:
        return CollectionItem.objects.create(**kwargs)
    finally:
        post_save.connect(
            sync_issue_rating_from_collection_item,
            sender=CollectionItem,
            dispatch_uid="post_save_sync_issue_rating_from_collection_item",
        )


def run_backfill(**options):
    out = io.StringIO()
    call_command("backfill_issue_ratings", stdout=out, **options)
    return out.getvalue()


def test_backfill_creates_missing_issue_ratings(rating_issue, rating_user):
    item = create_legacy_rated_item(issue=rating_issue, user=rating_user, rating=4)
    assert not IssueRating.objects.filter(issue=item.issue, user=item.user).exists()

    output = run_backfill()

    rating = IssueRating.objects.get(issue=item.issue, user=item.user)
    assert rating.rating == 4
    assert "1 to create" in output


def test_backfill_updates_conflicting_issue_ratings(rating_issue, rating_user):
    item = create_legacy_rated_item(issue=rating_issue, user=rating_user, rating=5)
    IssueRating.objects.create(issue=item.issue, user=item.user, rating=2)

    output = run_backfill()

    rating = IssueRating.objects.get(issue=item.issue, user=item.user)
    assert rating.rating == 5
    assert "1 to update" in output


def test_backfill_leaves_matching_ratings_unchanged(rating_issue, rating_user):
    item = create_legacy_rated_item(issue=rating_issue, user=rating_user, rating=3)
    IssueRating.objects.create(issue=item.issue, user=item.user, rating=3)

    output = run_backfill()

    assert "1 already in sync" in output


def test_backfill_ignores_collection_items_without_rating(rating_issue, rating_user):
    create_legacy_rated_item(issue=rating_issue, user=rating_user, rating=None)

    output = run_backfill()

    assert not IssueRating.objects.filter(issue=rating_issue, user=rating_user).exists()
    assert "0 rated collection item(s)" in output


def test_backfill_dry_run_makes_no_changes(rating_issue, rating_user):
    item = create_legacy_rated_item(issue=rating_issue, user=rating_user, rating=4)

    output = run_backfill(dry_run=True)

    assert not IssueRating.objects.filter(issue=item.issue, user=item.user).exists()
    assert "Would sync" in output
    assert "1 to create" in output


def test_backfill_is_idempotent(rating_issue, rating_user):
    create_legacy_rated_item(issue=rating_issue, user=rating_user, rating=4)

    run_backfill()
    second_run_output = run_backfill()

    assert "0 to create, 0 to update" in second_run_output
