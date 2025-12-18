"""Tests for the Reading List API."""

from django.urls import reverse
from rest_framework import status

from reading_lists.models import ReadingList


# List Endpoint Tests - Permissions
def test_unauthenticated_list_requires_auth(api_client):
    """Unauthenticated users require authentication to list reading lists."""
    resp = api_client.get(reverse("api:reading_list-list"))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_user_sees_public_and_own_lists(
    api_client,
    create_user,
    public_reading_list,
    private_reading_list,
    other_user_reading_list,
):
    """Authenticated users should see public lists and their own lists."""
    # Login as the reading list owner
    api_client.force_authenticate(user=private_reading_list.user)
    resp = api_client.get(reverse("api:reading_list-list"))
    assert resp.status_code == status.HTTP_200_OK
    # Should see: their public list, their private list, and other user's public list
    assert resp.data["count"] == 3
    list_names = {item["name"] for item in resp.data["results"]}
    assert "Public Reading List" in list_names
    assert "Private Reading List" in list_names
    assert "Other User's List" in list_names


def test_admin_sees_public_own_and_metron_lists(
    api_client,
    admin_user,
    public_reading_list,
    metron_reading_list,
    metron_private_reading_list,
):
    """Admin users should see public lists, their own lists, and Metron's lists."""
    api_client.force_authenticate(user=admin_user)
    resp = api_client.get(reverse("api:reading_list-list"))
    assert resp.status_code == status.HTTP_200_OK
    # Should see public list, Metron's public list, and Metron's private list
    assert resp.data["count"] >= 3
    list_names = {item["name"] for item in resp.data["results"]}
    assert "Public Reading List" in list_names
    assert "Metron's Reading List" in list_names
    assert "Metron's Private List" in list_names


# Retrieve Endpoint Tests
def test_unauthenticated_retrieve_requires_auth(api_client, public_reading_list):
    """Unauthenticated users require authentication to retrieve reading lists."""
    resp = api_client.get(reverse("api:reading_list-detail", kwargs={"pk": public_reading_list.pk}))
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_authenticated_can_retrieve_own_private_list(api_client, private_reading_list):
    """Authenticated users can retrieve their own private reading lists."""
    api_client.force_authenticate(user=private_reading_list.user)
    resp = api_client.get(
        reverse("api:reading_list-detail", kwargs={"pk": private_reading_list.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["name"] == "Private Reading List"


def test_authenticated_cannot_retrieve_other_users_private_list(
    api_client, create_user, private_reading_list
):
    """Authenticated users cannot retrieve another user's private reading lists."""
    other_user = create_user(username="different_user")
    api_client.force_authenticate(user=other_user)
    resp = api_client.get(
        reverse("api:reading_list-detail", kwargs={"pk": private_reading_list.pk})
    )
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def test_admin_can_retrieve_metron_private_list(
    api_client, admin_user, metron_private_reading_list
):
    """Admin users can retrieve Metron's private reading lists."""
    api_client.force_authenticate(user=admin_user)
    resp = api_client.get(
        reverse("api:reading_list-detail", kwargs={"pk": metron_private_reading_list.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["name"] == "Metron's Private List"


def test_get_invalid_reading_list(api_client_with_credentials):
    """Test retrieving a non-existent reading list returns 404."""
    resp = api_client_with_credentials.get(reverse("api:reading_list-detail", kwargs={"pk": 99999}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# Items Action Tests
def test_retrieve_reading_list_items(api_client_with_credentials, reading_list_with_issues):
    """Test retrieving items for a reading list."""
    resp = api_client_with_credentials.get(
        reverse("api:reading_list-items", kwargs={"pk": reading_list_with_issues.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 3
    # Verify items are ordered correctly
    assert resp.data["results"][0]["order"] == 1
    assert resp.data["results"][1]["order"] == 2
    assert resp.data["results"][2]["order"] == 3


def test_items_include_issue_data(api_client_with_credentials, reading_list_with_issues):
    """Test that items include nested issue data."""
    resp = api_client_with_credentials.get(
        reverse("api:reading_list-items", kwargs={"pk": reading_list_with_issues.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    # Check that issue data is included
    first_item = resp.data["results"][0]
    assert "issue" in first_item
    assert "id" in first_item["issue"]
    assert "series" in first_item["issue"]


def test_items_pagination(api_client_with_credentials, reading_list_with_issues):
    """Test that items are paginated."""
    resp = api_client_with_credentials.get(
        reverse("api:reading_list-items", kwargs={"pk": reading_list_with_issues.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    # Check pagination structure
    assert "count" in resp.data
    assert "next" in resp.data
    assert "previous" in resp.data
    assert "results" in resp.data


def test_items_requires_authentication(api_client, reading_list_with_issues):
    """Test that items action requires authentication."""
    resp = api_client.get(
        reverse("api:reading_list-items", kwargs={"pk": reading_list_with_issues.pk})
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_items_respects_permissions(api_client, create_user):
    """Test that authenticated users cannot access items of another user's private list."""

    user = create_user()
    other_user = create_user(username="other")
    private_list = ReadingList.objects.create(
        user=user,
        name="Private List",
        is_private=True,
    )
    # Authenticated user (other) cannot access another user's private list items
    api_client.force_authenticate(user=other_user)
    resp = api_client.get(reverse("api:reading_list-items", kwargs={"pk": private_list.pk}))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


# Read-Only Tests
def test_post_not_allowed(api_client_with_staff_credentials):
    """Test that POST is not allowed on reading list endpoint."""
    data = {
        "name": "New Reading List",
        "desc": "Test description",
        "is_private": False,
    }
    resp = api_client_with_staff_credentials.post(reverse("api:reading_list-list"), data=data)
    # Returns 403 because DjangoModelPermissions checks permissions before method
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_put_not_allowed(api_client_with_staff_credentials, public_reading_list):
    """Test that PUT is not allowed on reading list endpoint."""
    data = {
        "name": "Updated Name",
        "desc": "Updated description",
        "is_private": False,
    }
    resp = api_client_with_staff_credentials.put(
        reverse("api:reading_list-detail", kwargs={"pk": public_reading_list.pk}), data=data
    )
    # Returns 403 because DjangoModelPermissions checks permissions before method
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_patch_not_allowed(api_client_with_staff_credentials, public_reading_list):
    """Test that PATCH is not allowed on reading list endpoint."""
    data = {"name": "Updated Name"}
    resp = api_client_with_staff_credentials.patch(
        reverse("api:reading_list-detail", kwargs={"pk": public_reading_list.pk}), data=data
    )
    # Returns 403 because DjangoModelPermissions checks permissions before method
    assert resp.status_code == status.HTTP_403_FORBIDDEN


def test_delete_not_allowed(api_client_with_staff_credentials, public_reading_list):
    """Test that DELETE is not allowed on reading list endpoint."""
    resp = api_client_with_staff_credentials.delete(
        reverse("api:reading_list-detail", kwargs={"pk": public_reading_list.pk})
    )
    # Returns 403 because DjangoModelPermissions checks permissions before method
    assert resp.status_code == status.HTTP_403_FORBIDDEN


# Filtering Tests
def test_filter_by_name(api_client_with_credentials, public_reading_list, reading_list_with_issues):
    """Test filtering reading lists by name."""
    resp = api_client_with_credentials.get(reverse("api:reading_list-list"), {"name": "Public"})
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == "Public Reading List"


def test_filter_by_username(
    api_client_with_credentials, reading_list_user, public_reading_list, other_user_reading_list
):
    """Test filtering reading lists by username."""
    resp = api_client_with_credentials.get(
        reverse("api:reading_list-list"), {"username": reading_list_user.username}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert resp.data["count"] == 1
    assert resp.data["results"][0]["name"] == "Public Reading List"


# Response Structure Tests
def test_list_response_structure(api_client_with_credentials, public_reading_list):
    """Test that list response has the expected structure."""
    resp = api_client_with_credentials.get(reverse("api:reading_list-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "count" in resp.data
    assert "next" in resp.data
    assert "previous" in resp.data
    assert "results" in resp.data
    # Check list item structure (uses ReadingListListSerializer)
    if resp.data["results"]:
        item = resp.data["results"][0]
        assert "id" in item
        assert "name" in item
        assert "user" in item


def test_detail_response_structure(api_client_with_credentials, reading_list_with_issues):
    """Test that detail response has the expected structure."""
    resp = api_client_with_credentials.get(
        reverse("api:reading_list-detail", kwargs={"pk": reading_list_with_issues.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    # Check detail structure (uses ReadingListReadSerializer)
    assert "id" in resp.data
    assert "name" in resp.data
    assert "desc" in resp.data
    assert "user" in resp.data
    assert "is_private" in resp.data
    assert "attribution_source" in resp.data
    assert "attribution_url" in resp.data


def test_items_response_structure(api_client_with_credentials, reading_list_with_issues):
    """Test that items response has the expected structure."""
    resp = api_client_with_credentials.get(
        reverse("api:reading_list-items", kwargs={"pk": reading_list_with_issues.pk})
    )
    assert resp.status_code == status.HTTP_200_OK
    # Check items structure (uses ReadingListItemSerializer)
    if resp.data["results"]:
        item = resp.data["results"][0]
        assert "id" in item
        assert "issue" in item
        assert "order" in item
        assert "issue_type" in item
        # Check nested issue structure
        assert "id" in item["issue"]
        assert "series" in item["issue"]
