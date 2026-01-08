"""Tests for the scrobble action on Collection API."""

from datetime import datetime, timezone

from django.urls import reverse
from rest_framework import status

from user_collection.models import CollectionItem


# Authentication Tests
def test_unauthenticated_scrobble_requires_auth(api_client, collection_issue_1):
    """Unauthenticated users require authentication to scrobble."""
    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_user_can_scrobble(api_client, collection_user, collection_issue_1):
    """Authenticated users can scrobble issues."""
    api_client.force_authenticate(user=collection_user)
    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id},
    )
    assert resp.status_code == status.HTTP_201_CREATED


# Create New Item Tests
def test_scrobble_new_issue_creates_collection_item(
    api_client, collection_user, collection_issue_1
):
    """Scrobbling a new issue creates a collection item with 201."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["created"] is True
    assert resp.data["issue"]["id"] == collection_issue_1.id
    assert resp.data["is_read"] is True
    assert resp.data["date_read"] is not None

    # Verify item was created in database
    item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
    assert item.quantity == 1
    assert item.book_format == CollectionItem.BookFormat.DIGITAL
    assert item.is_read is True
    assert item.date_read is not None


def test_scrobble_new_issue_defaults_to_digital_format(
    api_client, collection_user, collection_issue_1
):
    """New collection items created by scrobble default to DIGITAL format."""
    api_client.force_authenticate(user=collection_user)

    api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id},
    )

    item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
    assert item.book_format == CollectionItem.BookFormat.DIGITAL


def test_scrobble_with_explicit_datetime(api_client, collection_user, collection_issue_1):
    """Can provide explicit date_read datetime."""
    api_client.force_authenticate(user=collection_user)

    explicit_datetime = "2024-06-15T14:30:00Z"
    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "date_read": explicit_datetime},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    # Check that date_read is set (may be in different timezone)
    assert resp.data["date_read"] is not None
    assert "2024-06-15" in resp.data["date_read"]


def test_scrobble_with_rating(api_client, collection_user, collection_issue_1):
    """Can provide rating (1-5) when scrobbling."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "rating": 5},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["rating"] == 5

    item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
    assert item.rating == 5


# Update Existing Item Tests
def test_scrobble_existing_issue_returns_200(api_client, collection_user, collection_item):
    """Scrobbling an existing collection item returns 200."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_item.issue.id},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["created"] is False


def test_scrobble_updates_is_read_and_date_read(api_client, collection_user, collection_item):
    """Scrobbling updates is_read and date_read on existing items."""
    api_client.force_authenticate(user=collection_user)

    # Ensure item starts as unread
    collection_item.is_read = False
    collection_item.date_read = None
    collection_item.save()

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_item.issue.id},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["is_read"] is True
    assert resp.data["date_read"] is not None

    # Verify database was updated
    collection_item.refresh_from_db()
    assert collection_item.is_read is True
    assert collection_item.date_read is not None


def test_scrobble_updates_rating_if_provided(api_client, collection_user, collection_item):
    """Scrobbling updates rating if provided."""
    api_client.force_authenticate(user=collection_user)

    collection_item.rating = None
    collection_item.save()

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_item.issue.id, "rating": 4},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["rating"] == 4

    collection_item.refresh_from_db()
    assert collection_item.rating == 4


def test_scrobble_doesnt_change_quantity(api_client, collection_user, collection_item):
    """Scrobbling doesn't change quantity on existing items."""
    api_client.force_authenticate(user=collection_user)

    collection_item.quantity = 5
    collection_item.save()

    api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_item.issue.id},
    )

    collection_item.refresh_from_db()
    assert collection_item.quantity == 5


def test_scrobble_doesnt_change_book_format(api_client, collection_user, collection_item):
    """Scrobbling doesn't change book_format on existing items."""
    api_client.force_authenticate(user=collection_user)

    collection_item.book_format = CollectionItem.BookFormat.PRINT
    collection_item.save()

    api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_item.issue.id},
    )

    collection_item.refresh_from_db()
    assert collection_item.book_format == CollectionItem.BookFormat.PRINT


def test_scrobble_overwrites_previous_date_read(api_client, collection_user, collection_item):
    """Scrobbling overwrites previous date_read."""
    api_client.force_authenticate(user=collection_user)

    old_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
    collection_item.date_read = old_date
    collection_item.save()

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_item.issue.id},
    )
    assert resp.status_code == status.HTTP_200_OK

    collection_item.refresh_from_db()
    assert collection_item.date_read != old_date


def test_scrobble_without_rating_keeps_existing_rating(
    api_client, collection_user, collection_item
):
    """Scrobbling without rating doesn't change existing rating."""
    api_client.force_authenticate(user=collection_user)

    collection_item.rating = 3
    collection_item.save()

    api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_item.issue.id},
    )

    collection_item.refresh_from_db()
    assert collection_item.rating == 3


# Validation Tests
def test_scrobble_nonexistent_issue_returns_404(api_client, collection_user):
    """Scrobbling a non-existent issue returns 400 (validation error)."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": 99999},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "issue_id" in resp.data


def test_scrobble_invalid_rating_below_min_returns_400(
    api_client, collection_user, collection_issue_1
):
    """Rating < 1 returns 400."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "rating": 0},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "rating" in resp.data


def test_scrobble_invalid_rating_above_max_returns_400(
    api_client, collection_user, collection_issue_1
):
    """Rating > 5 returns 400."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "rating": 6},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "rating" in resp.data


def test_scrobble_invalid_datetime_format_returns_400(
    api_client, collection_user, collection_issue_1
):
    """Invalid date_read format returns 400."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "date_read": "not-a-datetime"},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "date_read" in resp.data


def test_scrobble_missing_issue_id_returns_400(api_client, collection_user):
    """Empty request body returns 400."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(reverse("api:collection-scrobble"), {})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "issue_id" in resp.data


# User Isolation Tests
def test_multiple_users_can_scrobble_same_issue(
    api_client, collection_user, other_collection_user, collection_issue_1
):
    """Multiple users can independently scrobble the same issue."""
    # User 1 scrobbles
    api_client.force_authenticate(user=collection_user)
    resp1 = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "rating": 5},
    )
    assert resp1.status_code == status.HTTP_201_CREATED

    # User 2 scrobbles same issue
    api_client.force_authenticate(user=other_collection_user)
    resp2 = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "rating": 3},
    )
    assert resp2.status_code == status.HTTP_201_CREATED

    # Verify both users have independent items
    item1 = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
    item2 = CollectionItem.objects.get(user=other_collection_user, issue=collection_issue_1)
    assert item1.rating == 5
    assert item2.rating == 3
    assert item1.id != item2.id


def test_scrobble_only_affects_current_user(
    api_client, collection_user, other_collection_user, collection_issue_1
):
    """User's scrobble doesn't affect other users' collections."""
    # Create item for other_user
    other_item = CollectionItem.objects.create(
        user=other_collection_user,
        issue=collection_issue_1,
        is_read=False,
        rating=None,
    )

    # User 1 scrobbles
    api_client.force_authenticate(user=collection_user)
    api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "rating": 5},
    )

    # Verify other_user's item unchanged
    other_item.refresh_from_db()
    assert other_item.is_read is False
    assert other_item.rating is None


# Response Structure Tests
def test_scrobble_response_includes_issue_details(api_client, collection_user, collection_issue_1):
    """Response includes full issue details."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert "issue" in resp.data
    assert resp.data["issue"]["id"] == collection_issue_1.id
    assert "series" in resp.data["issue"]
    assert "number" in resp.data["issue"]


def test_scrobble_response_includes_created_flag(api_client, collection_user, collection_issue_1):
    """Response includes created flag."""
    api_client.force_authenticate(user=collection_user)

    # First scrobble (creates)
    resp1 = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id},
    )
    assert resp1.data["created"] is True

    # Second scrobble (updates)
    resp2 = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id},
    )
    assert resp2.data["created"] is False


def test_scrobble_response_includes_all_expected_fields(
    api_client, collection_user, collection_issue_1
):
    """Response includes all expected fields."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-scrobble"),
        {"issue_id": collection_issue_1.id, "rating": 4},
    )
    assert resp.status_code == status.HTTP_201_CREATED

    expected_fields = ["id", "issue", "is_read", "date_read", "rating", "created", "modified"]
    for field in expected_fields:
        assert field in resp.data
