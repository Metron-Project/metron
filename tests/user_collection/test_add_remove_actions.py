"""Tests for the add action and destroy endpoint on Collection API."""

from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from user_collection.models import CollectionItem


# Add Action - Authentication
def test_unauthenticated_add_requires_auth(api_client, collection_issue_1):
    """Unauthenticated users require authentication to add an issue."""
    resp = api_client.post(
        reverse("api:collection-add"),
        {"issue_id": collection_issue_1.id},
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# Add Action - Create New Item
def test_add_new_issue_creates_collection_item(api_client, collection_user, collection_issue_1):
    """Adding a new issue creates a collection item with 201."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-add"),
        {"issue_id": collection_issue_1.id},
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["issue"]["id"] == collection_issue_1.id
    assert resp.data["is_read"] is False

    item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
    assert item.quantity == 1
    assert item.book_format == CollectionItem.BookFormat.PRINT
    assert item.is_read is False


def test_add_new_issue_with_details(api_client, collection_user, collection_issue_1):
    """Adding an issue accepts optional collection metadata."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-add"),
        {
            "issue_id": collection_issue_1.id,
            "quantity": 3,
            "book_format": "DIGITAL",
            "grade": "9.8",
            "grading_company": "CGC",
            "purchase_date": "2023-06-15",
            "purchase_price": "4.99",
            "purchase_store": "Local Comic Shop",
            "storage_location": "Long Box 3",
            "notes": "First printing",
        },
    )
    assert resp.status_code == status.HTTP_201_CREATED

    item = CollectionItem.objects.get(user=collection_user, issue=collection_issue_1)
    assert item.quantity == 3
    assert item.book_format == CollectionItem.BookFormat.DIGITAL
    assert item.grade == Decimal("9.8")
    assert item.grading_company == CollectionItem.GradingCompany.CGC
    assert item.purchase_price.amount == Decimal("4.99")
    assert item.purchase_store == "Local Comic Shop"
    assert item.storage_location == "Long Box 3"
    assert item.notes == "First printing"


def test_add_missing_issue_returns_400(api_client, collection_user):
    """Adding a non-existent issue returns a validation error."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-add"),
        {"issue_id": 99999},
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


# Add Action - Existing Item is Idempotent
def test_add_existing_issue_returns_200_unchanged(api_client, collection_user, collection_item):
    """Adding an issue already in the collection returns the existing item unchanged."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.post(
        reverse("api:collection-add"),
        {"issue_id": collection_item.issue.id, "quantity": 5, "book_format": "DIGITAL"},
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["id"] == collection_item.pk

    collection_item.refresh_from_db()
    assert collection_item.quantity == 1
    assert collection_item.book_format == CollectionItem.BookFormat.PRINT


# Destroy Endpoint
def test_unauthenticated_destroy_requires_auth(api_client, collection_item):
    """Unauthenticated users require authentication to remove a collection item."""
    resp = api_client.delete(reverse("api:collection-detail", kwargs={"pk": collection_item.pk}))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_can_remove_own_item(api_client, collection_item):
    """Authenticated users can remove their own collection items."""
    api_client.force_authenticate(user=collection_item.user)

    resp = api_client.delete(reverse("api:collection-detail", kwargs={"pk": collection_item.pk}))
    assert resp.status_code == status.HTTP_204_NO_CONTENT
    assert not CollectionItem.objects.filter(pk=collection_item.pk).exists()


def test_authenticated_cannot_remove_other_users_item(
    api_client, other_collection_user, collection_item
):
    """Users cannot remove another user's collection item."""
    api_client.force_authenticate(user=other_collection_user)

    resp = api_client.delete(reverse("api:collection-detail", kwargs={"pk": collection_item.pk}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND
    assert CollectionItem.objects.filter(pk=collection_item.pk).exists()


def test_destroy_nonexistent_item_returns_404(api_client_with_credentials):
    """Removing a non-existent collection item returns 404."""
    resp = api_client_with_credentials.delete(
        reverse("api:collection-detail", kwargs={"pk": 99999})
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND
