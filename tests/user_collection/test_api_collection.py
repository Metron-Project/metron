"""Tests for the Collection API."""

from datetime import date, datetime, timezone
from decimal import Decimal

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
        user=collection_user,
        issue=collection_issue_1,
        is_read=True,
        date_read=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )
    CollectionItem.objects.create(
        user=collection_user,
        issue=collection_issue_2,
        is_read=True,
        date_read=datetime(2024, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
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


# Grading and Rating Tests
def test_list_includes_grade_fields(
    api_client, collection_user, collection_item_professionally_graded
):
    """Test that list response includes grade and grading company fields."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.get(reverse("api:collection-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1

    item = resp.data["results"][0]
    assert "grade" in item
    assert "grading_company" in item
    assert item["grade"] == Decimal("9.8")
    assert item["grading_company"] == "CGC (Certified Guaranty Company)"


def test_detail_includes_grade_fields(
    api_client, collection_user, collection_item_professionally_graded
):
    """Test that detail response includes grade and grading company fields."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.get(
        reverse("api:collection-detail", kwargs={"pk": collection_item_professionally_graded.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["grade"] == Decimal("9.8")
    assert resp.data["grading_company"] == "CGC (Certified Guaranty Company)"


def test_list_includes_rating_field(api_client, collection_user, collection_item_read):
    """Test that list response includes rating field."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.get(reverse("api:collection-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1

    item = resp.data["results"][0]
    assert "rating" in item
    assert item["rating"] == 4


def test_detail_includes_rating_field(api_client, collection_user, collection_item_read):
    """Test that detail response includes rating field."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.get(reverse("api:collection-detail", kwargs={"pk": collection_item_read.pk}))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["rating"] == 4


def test_user_graded_item_has_empty_grading_company(
    api_client, collection_user, collection_item_user_graded
):
    """Test that user-assessed grades have empty grading company."""
    api_client.force_authenticate(user=collection_user)

    resp = api_client.get(
        reverse("api:collection-detail", kwargs={"pk": collection_item_user_graded.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["grade"] == Decimal("8.5")
    assert resp.data["grading_company"] == ""


# Filter Tests for Grading and Rating
def test_filter_by_grade(
    api_client,
    collection_user,
    collection_item_professionally_graded,
    collection_item_user_graded,
):
    """Test filtering collection by grade."""
    api_client.force_authenticate(user=collection_user)

    # Filter by 9.8 grade
    resp = api_client.get(reverse("api:collection-list"), {"grade": "9.8"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["grade"] == Decimal("9.8")

    # Filter by 8.5 grade
    resp = api_client.get(reverse("api:collection-list"), {"grade": "8.5"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["grade"] == Decimal("8.5")


def test_filter_by_grading_company(
    api_client,
    collection_user,
    collection_item_professionally_graded,
    collection_item_user_graded,
):
    """Test filtering collection by grading company."""
    api_client.force_authenticate(user=collection_user)

    # Filter by CGC
    resp = api_client.get(reverse("api:collection-list"), {"grading_company": "CGC"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["grading_company"] == "CGC (Certified Guaranty Company)"


def test_filter_by_rating(api_client, collection_user, collection_issue_1, collection_issue_2):
    """Test filtering collection by rating."""
    api_client.force_authenticate(user=collection_user)

    # Create items with different ratings
    CollectionItem.objects.create(
        user=collection_user, issue=collection_issue_1, is_read=True, rating=5
    )
    CollectionItem.objects.create(
        user=collection_user, issue=collection_issue_2, is_read=True, rating=3
    )

    # Filter by 5-star rating
    resp = api_client.get(reverse("api:collection-list"), {"rating": "5"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["rating"] == 5

    # Filter by 3-star rating
    resp = api_client.get(reverse("api:collection-list"), {"rating": "3"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["rating"] == 3


# Missing Series Endpoint Tests
def test_unauthenticated_missing_series_requires_auth(api_client):
    """Unauthenticated users require authentication to view missing series."""
    resp = api_client.get(reverse("api:collection-missing-series"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_missing_series_returns_incomplete_series(
    api_client,
    collection_user,
    collection_series,
    collection_issue_1,
    collection_issue_2,
    create_user,
):
    """Test that missing_series returns series where user owns some but not all issues."""
    api_client.force_authenticate(user=collection_user)

    # Create a third issue in the series
    user = create_user()

    collection_issue_1.__class__.objects.create(
        series=collection_series,
        number="3",
        slug="collection-series-3",
        cover_date=date(2023, 3, 1),
        edited_by=user,
        created_by=user,
    )

    # User owns issues 1 and 2, but not issue 3
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1, quantity=1)
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_2, quantity=1)

    resp = api_client.get(reverse("api:collection-missing-series"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1

    series_data = resp.data["results"][0]
    assert series_data["id"] == collection_series.id
    assert series_data["name"] == collection_series.name
    assert series_data["total_issues"] == 3
    assert series_data["owned_issues"] == 2
    assert series_data["missing_count"] == 1
    assert series_data["completion_percentage"] == 66.7


def test_missing_series_excludes_complete_series(
    api_client, collection_user, collection_series, collection_issue_1, collection_issue_2
):
    """Test that series with all issues owned are excluded."""
    api_client.force_authenticate(user=collection_user)

    # User owns all issues in the series
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1, quantity=1)
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_2, quantity=1)

    resp = api_client.get(reverse("api:collection-missing-series"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_missing_series_excludes_unowned_series(
    api_client, collection_user, collection_series, collection_issue_1
):
    """Test that series with no owned issues are excluded."""
    api_client.force_authenticate(user=collection_user)

    # Don't create any collection items
    resp = api_client.get(reverse("api:collection-missing-series"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_missing_series_only_shows_user_data(
    api_client,
    collection_user,
    other_collection_user,
    collection_series,
    collection_issue_1,
    collection_issue_2,
    create_user,
):
    """Test that missing_series only shows data for the authenticated user."""
    user = create_user()
    issue_3 = collection_issue_1.__class__.objects.create(
        series=collection_series,
        number="3",
        slug="collection-series-3",
        cover_date=date(2023, 3, 1),
        edited_by=user,
        created_by=user,
    )

    # collection_user owns 1 issue
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1, quantity=1)

    # other_collection_user owns all 3 issues
    CollectionItem.objects.create(user=other_collection_user, issue=collection_issue_1, quantity=1)
    CollectionItem.objects.create(user=other_collection_user, issue=collection_issue_2, quantity=1)
    CollectionItem.objects.create(user=other_collection_user, issue=issue_3, quantity=1)

    # Authenticate as collection_user
    api_client.force_authenticate(user=collection_user)
    resp = api_client.get(reverse("api:collection-missing-series"))
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["owned_issues"] == 1
    assert resp.data["results"][0]["missing_count"] == 2

    # Authenticate as other_collection_user
    api_client.force_authenticate(user=other_collection_user)
    resp = api_client.get(reverse("api:collection-missing-series"))
    assert resp.status_code == status.HTTP_200_OK
    # other_collection_user has complete series, so no missing issues
    assert resp.data["count"] == 0


# Missing Issues Endpoint Tests
def test_unauthenticated_missing_issues_requires_auth(api_client, collection_series):
    """Unauthenticated users require authentication to view missing issues."""
    resp = api_client.get(
        reverse("api:collection-missing-issues", kwargs={"series_id": collection_series.id})
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_missing_issues_returns_unowned_issues(
    api_client, collection_user, collection_series, collection_issue_1, collection_issue_2
):
    """Test that missing_issues returns issues not in user's collection."""
    api_client.force_authenticate(user=collection_user)

    # User owns issue 1 but not issue 2
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1, quantity=1)

    resp = api_client.get(
        reverse("api:collection-missing-issues", kwargs={"series_id": collection_series.id})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == collection_issue_2.id
    assert resp.data["results"][0]["number"] == "2"


def test_missing_issues_excludes_owned_issues(
    api_client, collection_user, collection_series, collection_issue_1, collection_issue_2
):
    """Test that owned issues are excluded from missing issues list."""
    api_client.force_authenticate(user=collection_user)

    # User owns both issues
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1, quantity=1)
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_2, quantity=1)

    resp = api_client.get(
        reverse("api:collection-missing-issues", kwargs={"series_id": collection_series.id})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 0


def test_missing_issues_only_shows_user_data(
    api_client,
    collection_user,
    other_collection_user,
    collection_series,
    collection_issue_1,
    collection_issue_2,
):
    """Test that missing_issues only considers the authenticated user's collection."""
    # collection_user owns issue 1
    CollectionItem.objects.create(user=collection_user, issue=collection_issue_1, quantity=1)

    # other_collection_user owns issue 2
    CollectionItem.objects.create(user=other_collection_user, issue=collection_issue_2, quantity=1)

    # Authenticate as collection_user - should see issue 2 as missing
    api_client.force_authenticate(user=collection_user)
    resp = api_client.get(
        reverse("api:collection-missing-issues", kwargs={"series_id": collection_series.id})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == collection_issue_2.id

    # Authenticate as other_collection_user - should see issue 1 as missing
    api_client.force_authenticate(user=other_collection_user)
    resp = api_client.get(
        reverse("api:collection-missing-issues", kwargs={"series_id": collection_series.id})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["id"] == collection_issue_1.id


def test_missing_issues_returns_all_if_none_owned(
    api_client, collection_user, collection_series, collection_issue_1, collection_issue_2
):
    """Test that all issues are returned if user owns none."""
    api_client.force_authenticate(user=collection_user)

    # User doesn't own any issues
    resp = api_client.get(
        reverse("api:collection-missing-issues", kwargs={"series_id": collection_series.id})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 2
