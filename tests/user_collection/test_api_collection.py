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


# Create Endpoint Tests
def test_unauthenticated_create_requires_auth(api_client, collection_issue_1):
    """Unauthenticated users require authentication to create collection items."""
    data = {"issue": collection_issue_1.pk, "quantity": 1, "book_format": "PRINT"}
    resp = api_client.post(reverse("api:collection-list"), data=data)
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_can_create_item(api_client, collection_user, collection_issue_1):
    """Authenticated users can create collection items."""
    api_client.force_authenticate(user=collection_user)
    data = {
        "issue": collection_issue_1.pk,
        "quantity": 2,
        "book_format": "DIGITAL",
        "purchase_date": "2023-06-15",
        "purchase_price": "4.99",
        "purchase_store": "ComiXology",
        "storage_location": "Digital Library",
        "notes": "Sale purchase",
    }
    resp = api_client.post(reverse("api:collection-list"), data=data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["quantity"] == 2
    assert resp.data["book_format"] == "DIGITAL"

    # Verify item was created in database
    item = CollectionItem.objects.get(pk=resp.data["id"])
    assert item.user == collection_user
    assert item.issue == collection_issue_1


def test_create_duplicate_issue_fails(api_client, collection_user, collection_item):
    """Creating a collection item for an already-owned issue should fail."""
    api_client.force_authenticate(user=collection_user)
    data = {"issue": collection_item.issue.pk, "quantity": 1, "book_format": "PRINT"}
    resp = api_client.post(reverse("api:collection-list"), data=data, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "issue" in resp.data


def test_create_with_minimal_data(api_client, collection_user, collection_issue_2):
    """Test creating item with only required fields."""
    api_client.force_authenticate(user=collection_user)
    data = {"issue": collection_issue_2.pk}
    resp = api_client.post(reverse("api:collection-list"), data=data, format="json")
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["quantity"] == 1  # Default value
    assert resp.data["book_format"] == "PRINT"  # Default value


# Update Endpoint Tests
def test_unauthenticated_update_requires_auth(api_client, collection_item):
    """Unauthenticated users require authentication to update collection items."""
    data = {"quantity": 3}
    resp = api_client.patch(
        reverse("api:collection-detail", kwargs={"pk": collection_item.pk}),
        data=data,
        format="json",
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_can_update_own_item(api_client, collection_item):
    """Authenticated users can update their own collection items."""
    api_client.force_authenticate(user=collection_item.user)
    data = {"quantity": 3, "notes": "Updated notes"}
    resp = api_client.patch(
        reverse("api:collection-detail", kwargs={"pk": collection_item.pk}),
        data=data,
        format="json",
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["quantity"] == 3
    assert resp.data["notes"] == "Updated notes"

    # Verify in database
    collection_item.refresh_from_db()
    assert collection_item.quantity == 3


def test_authenticated_cannot_update_other_users_item(
    api_client, other_collection_user, collection_item
):
    """Authenticated users cannot update another user's collection items."""
    api_client.force_authenticate(user=other_collection_user)
    data = {"quantity": 5}
    resp = api_client.patch(
        reverse("api:collection-detail", kwargs={"pk": collection_item.pk}),
        data=data,
        format="json",
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# Delete Endpoint Tests
def test_unauthenticated_delete_requires_auth(api_client, collection_item):
    """Unauthenticated users require authentication to delete collection items."""
    resp = api_client.delete(reverse("api:collection-detail", kwargs={"pk": collection_item.pk}))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_can_delete_own_item(api_client, collection_item):
    """Authenticated users can delete their own collection items."""
    api_client.force_authenticate(user=collection_item.user)
    item_pk = collection_item.pk
    resp = api_client.delete(reverse("api:collection-detail", kwargs={"pk": item_pk}))
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    # Verify item was deleted
    assert not CollectionItem.objects.filter(pk=item_pk).exists()


def test_authenticated_cannot_delete_other_users_item(
    api_client, other_collection_user, collection_item
):
    """Authenticated users cannot delete another user's collection items."""
    api_client.force_authenticate(user=other_collection_user)
    resp = api_client.delete(reverse("api:collection-detail", kwargs={"pk": collection_item.pk}))
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
