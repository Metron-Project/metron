"""Tests for the Collection API."""

from django.urls import reverse
from rest_framework import status

from user_collection.models import CollectionItem


# List Endpoint Tests - Authentication
def test_unauthenticated_list_requires_auth(api_client):
    """Unauthenticated users require authentication to list collection items."""
    resp = api_client.get(reverse("api:collection-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_user_sees_only_own_items(
    api_client,
    collection_user,
    other_collection_user,
    collection_item,
    collection_item_with_details,
):
    """Authenticated users should only see their own collection items."""
    # collection_item and collection_item_with_details belong to collection_user
    api_client.force_authenticate(user=collection_user)

    resp = api_client.get(reverse("api:collection-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 2  # Only collection_user's items

    # Verify items belong to the authenticated user
    for item in resp.data["results"]:
        assert item["user"]["username"] == collection_user.username


def test_user_cannot_see_other_users_items(
    api_client, collection_user, other_collection_user, collection_item
):
    """Users cannot see other users' collection items."""
    # Authenticate as other_collection_user
    api_client.force_authenticate(user=other_collection_user)

    resp = api_client.get(reverse("api:collection-list"))
    assert resp.status_code == status.HTTP_200_OK
    # other_collection_user has no items
    assert resp.data["count"] == 0


# Retrieve Endpoint Tests
def test_unauthenticated_retrieve_requires_auth(api_client, collection_item):
    """Unauthenticated users require authentication to retrieve collection items."""
    resp = api_client.get(reverse("api:collection-detail", kwargs={"pk": collection_item.pk}))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_can_retrieve_own_item(api_client, collection_item):
    """Authenticated users can retrieve their own collection items."""
    api_client.force_authenticate(user=collection_item.user)
    resp = api_client.get(reverse("api:collection-detail", kwargs={"pk": collection_item.pk}))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["id"] == collection_item.pk
    assert resp.data["quantity"] == 1


def test_authenticated_cannot_retrieve_other_users_item(
    api_client, collection_user, other_collection_user, collection_item
):
    """Authenticated users cannot retrieve another user's collection items."""
    # collection_item belongs to collection_user, authenticate as other_collection_user
    api_client.force_authenticate(user=other_collection_user)
    resp = api_client.get(reverse("api:collection-detail", kwargs={"pk": collection_item.pk}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_get_invalid_collection_item(api_client_with_credentials):
    """Test retrieving a non-existent collection item returns 404."""
    resp = api_client_with_credentials.get(reverse("api:collection-detail", kwargs={"pk": 99999}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# Stats Endpoint Tests
def test_unauthenticated_stats_requires_auth(api_client):
    """Unauthenticated users require authentication to view stats."""
    resp = api_client.get(reverse("api:collection-stats"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_can_view_stats(
    api_client, collection_user, collection_item, collection_item_with_details
):
    """Authenticated users can view their collection statistics."""
    api_client.force_authenticate(user=collection_user)
    resp = api_client.get(reverse("api:collection-stats"))
    assert resp.status_code == status.HTTP_200_OK

    assert resp.data["total_items"] == 2
    assert resp.data["total_quantity"] == 3  # 1 + 2
    assert "total_value" in resp.data
    assert "by_format" in resp.data


def test_stats_only_shows_user_data(
    api_client,
    collection_user,
    other_collection_user,
    collection_item,
    collection_issue_2,
    create_user,
):
    """Stats endpoint should only show data for the authenticated user."""
    # Create an item for other_collection_user
    issue = collection_issue_2
    CollectionItem.objects.create(
        user=other_collection_user,
        issue=issue,
        quantity=10,
    )

    api_client.force_authenticate(user=collection_user)
    resp = api_client.get(reverse("api:collection-stats"))
    assert resp.status_code == status.HTTP_200_OK

    # Should only count collection_user's item (quantity=1)
    assert resp.data["total_items"] == 1
    assert resp.data["total_quantity"] == 1


# Filter Tests
def test_filter_by_book_format(
    api_client, collection_user, collection_item, collection_item_with_details
):
    """Test filtering collection by book format."""
    api_client.force_authenticate(user=collection_user)

    # Filter by PRINT
    resp = api_client.get(reverse("api:collection-list"), {"book_format": "PRINT"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1

    # Filter by BOTH
    resp = api_client.get(reverse("api:collection-list"), {"book_format": "BOTH"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_filter_by_purchase_date(api_client, collection_user, collection_item_with_details):
    """Test filtering collection by purchase date."""
    api_client.force_authenticate(user=collection_user)

    # Filter by exact date
    resp = api_client.get(reverse("api:collection-list"), {"purchase_date": "2023-06-15"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1

    # Filter by date range (greater than)
    resp = api_client.get(reverse("api:collection-list"), {"purchase_date_gt": "2023-06-01"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_filter_by_purchase_store(api_client, collection_user, collection_item_with_details):
    """Test filtering collection by purchase store."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.get(reverse("api:collection-list"), {"purchase_store": "Comic Shop"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_filter_by_storage_location(api_client, collection_user, collection_item_with_details):
    """Test filtering collection by storage location."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.get(reverse("api:collection-list"), {"storage_location": "Long Box"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


# Read Tracking Filter Tests
def test_filter_by_is_read(api_client, collection_user, collection_issue_1, collection_issue_2):
    """Test filtering collection by read status."""
    api_client.force_authenticate(user=collection_user)

    # Create one read and one unread item
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1, is_read=True)
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_2, is_read=False)

    # Filter for read items
    resp = api_client.get(reverse("api:collection-list"), {"is_read": "true"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["is_read"] is True

    # Filter for unread items
    resp = api_client.get(reverse("api:collection-list"), {"is_read": "false"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["is_read"] is False


def test_filter_by_date_read(api_client, collection_user, collection_issue_1, collection_issue_2):
    """Test filtering collection by date read."""
    api_client.force_authenticate(user=collection_user)

    # Create items with different read dates
    CollectionItem.objects.create(
        user=collection_user, issue=collection_issue_1, is_read=True, date_read="2024-06-01"
    )
    CollectionItem.objects.create(
        user=collection_user, issue=collection_issue_2, is_read=True, date_read="2024-07-01"
    )

    # Filter by exact date
    resp = api_client.get(reverse("api:collection-list"), {"date_read": "2024-06-01"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1

    # Filter by date range
    resp = api_client.get(reverse("api:collection-list"), {"date_read_gte": "2024-06-15"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1


def test_stats_includes_read_tracking(
    api_client, collection_user, collection_issue_1, collection_issue_2
):
    """Test that stats endpoint includes read tracking statistics."""
    api_client.force_authenticate(user=collection_user)

    # Create one read and one unread item
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1, is_read=True)
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_2, is_read=False)

    resp = api_client.get(reverse("api:collection-stats"))
    assert resp.status_code == status.HTTP_200_OK
    assert "read_count" in resp.data
    assert "unread_count" in resp.data
    assert resp.data["read_count"] == 1
    assert resp.data["unread_count"] == 1
