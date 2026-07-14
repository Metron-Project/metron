"""Tests for PATCH/PUT updates on Collection API (rating only)."""

from django.urls import reverse
from rest_framework import status

from issue_ratings.models import IssueRating
from user_collection.models import CollectionItem, ReadDate


def test_unauthenticated_update_requires_auth(api_client, collection_item):
    """Unauthenticated users require authentication to update a collection item."""
    resp = api_client.patch(
        reverse("api:collection-detail", args=[collection_item.id]),
        {"rating": 4},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_patch_updates_rating(api_client, collection_user, collection_item):
    """PATCH updates the rating field."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.patch(
        reverse("api:collection-detail", args=[collection_item.id]),
        {"rating": 4},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["rating"] == 4

    collection_item.refresh_from_db()
    assert collection_item.rating == 4


def test_patch_rating_syncs_to_issue_rating(api_client, collection_user, collection_item):
    """PATCHing a collection item's rating syncs the community IssueRating too."""
    api_client.force_authenticate(user=collection_user)

    api_client.patch(
        reverse("api:collection-detail", args=[collection_item.id]),
        {"rating": 4},
    )
    rating = IssueRating.objects.get(issue=collection_item.issue, user=collection_user)
    assert rating.rating == 4


def test_patch_rating_creates_no_read_date_rows(api_client, collection_user, collection_item):
    """Updating rating via PATCH does not create any ReadDate rows."""
    api_client.force_authenticate(user=collection_user)

    assert ReadDate.objects.filter(collection_item=collection_item).count() == 0

    api_client.patch(
        reverse("api:collection-detail", args=[collection_item.id]),
        {"rating": 5},
    )

    assert ReadDate.objects.filter(collection_item=collection_item).count() == 0


def test_patch_ignores_is_read_and_date_read(api_client, collection_user, collection_item):
    """is_read/date_read in the PATCH body are ignored; only rating is applied."""
    api_client.force_authenticate(user=collection_user)

    collection_item.is_read = False
    collection_item.date_read = None
    collection_item.save()

    resp = api_client.patch(
        reverse("api:collection-detail", args=[collection_item.id]),
        {"rating": 3, "is_read": True, "date_read": "2024-06-15T14:30:00Z"},
    )
    assert resp.status_code == status.HTTP_200_OK

    collection_item.refresh_from_db()
    assert collection_item.rating == 3
    assert collection_item.is_read is False
    assert collection_item.date_read is None


def test_patch_rating_below_min_returns_400(api_client, collection_user, collection_item):
    """Rating < 1 returns 400."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.patch(
        reverse("api:collection-detail", args=[collection_item.id]),
        {"rating": 0},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "rating" in resp.data


def test_patch_rating_above_max_returns_400(api_client, collection_user, collection_item):
    """Rating > 5 returns 400."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.patch(
        reverse("api:collection-detail", args=[collection_item.id]),
        {"rating": 6},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "rating" in resp.data


def test_patch_other_users_collection_item_returns_404(
    api_client, collection_user, other_collection_user, collection_issue_1
):
    """A user cannot update another user's collection item."""
    other_item = CollectionItem.objects.create(
        user=other_collection_user,
        issue=collection_issue_1,
        quantity=1,
    )

    api_client.force_authenticate(user=collection_user)
    resp = api_client.patch(
        reverse("api:collection-detail", args=[other_item.id]),
        {"rating": 5},
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    other_item.refresh_from_db()
    assert other_item.rating is None
