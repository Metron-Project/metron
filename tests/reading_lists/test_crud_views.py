"""Tests for creating, updating and deleting reading lists."""

from django.urls import reverse

from reading_lists.models import ReadingList

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403


class TestReadingListCreateView:
    """Tests for the ReadingListCreateView."""

    def test_reading_list_create_view_requires_login(self, client):
        """Test that the view requires login."""
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_reading_list_create_view_get(self, client, reading_list_user, test_password):
        """Test GET request to create view."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context
        assert resp.context["title"] == "Create Reading List"
        assert resp.context["button_text"] == "Create"

    def test_reading_list_create_view_post(self, client, reading_list_user, test_password):
        """Test POST request to create a reading list."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:create")
        data = {
            "name": "New Reading List",
            "desc": "A new reading list",
            "is_private": False,
            "list_type": ReadingList.ListType.EVENT,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was created
        reading_list = ReadingList.objects.get(name="New Reading List")
        assert reading_list.user == reading_list_user
        assert reading_list.desc == "A new reading list"
        assert not reading_list.is_private


class TestReadingListUpdateView:
    """Tests for the ReadingListUpdateView."""

    def test_reading_list_update_view_requires_login(self, client, public_reading_list):
        """Test that the view requires login."""
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_reading_list_update_view_owner(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that owners can update their lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context
        assert resp.context["title"] == "Edit Reading List"
        assert resp.context["button_text"] == "Update"

    def test_reading_list_update_view_not_owner(
        self, client, other_user, public_reading_list, test_password
    ):
        """Test that non-owners cannot update lists."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_reading_list_update_view_post(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test POST request to update a reading list."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        data = {
            "name": "Updated Reading List",
            "desc": "An updated reading list",
            "is_private": True,
            "list_type": ReadingList.ListType.EVENT,
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was updated
        public_reading_list.refresh_from_db()
        assert public_reading_list.name == "Updated Reading List"
        assert public_reading_list.desc == "An updated reading list"
        assert public_reading_list.is_private


class TestReadingListDeleteView:
    """Tests for the ReadingListDeleteView."""

    def test_reading_list_delete_view_requires_login(self, client, public_reading_list):
        """Test that the view requires login."""
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_reading_list_delete_view_owner(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that owners can delete their lists."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK

    def test_reading_list_delete_view_not_owner(
        self, client, other_user, public_reading_list, test_password
    ):
        """Test that non-owners cannot delete lists."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_reading_list_delete_view_post(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test POST request to delete a reading list."""
        client.login(username=reading_list_user.username, password=test_password)
        list_id = public_reading_list.id
        url = reverse("reading-list:delete", args=[public_reading_list.slug])
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was deleted
        assert not ReadingList.objects.filter(id=list_id).exists()


class TestAttributionFieldRestrictions:
    """Tests for attribution field restrictions (admin-only)."""

    def test_create_view_non_admin_cannot_see_attribution_fields(
        self, client, reading_list_user, test_password
    ):
        """Test that non-admin users don't see attribution fields in create form."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Attribution fields should not be in the form for non-admin users
        assert "attribution_source" not in form.fields
        assert "attribution_url" not in form.fields
        # Regular fields should still be present
        assert "name" in form.fields
        assert "desc" in form.fields
        assert "is_private" in form.fields

    def test_create_view_admin_can_see_attribution_fields(self, client, admin_user, test_password):
        """Test that admin users see attribution fields in create form."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:create")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Admin users should see all fields including attribution fields
        assert "attribution_source" in form.fields
        assert "attribution_url" in form.fields
        assert "name" in form.fields
        assert "desc" in form.fields
        assert "is_private" in form.fields

    def test_create_view_non_admin_cannot_submit_attribution_fields(
        self, client, reading_list_user, test_password
    ):
        """Test that non-admin users cannot submit attribution fields."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:create")
        data = {
            "name": "New Reading List",
            "desc": "A new reading list",
            "is_private": False,
            "list_type": ReadingList.ListType.EVENT,
            "attribution_source": ReadingList.AttributionSource.CBRO,
            "attribution_url": "https://example.com/source",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was created WITHOUT attribution data
        reading_list = ReadingList.objects.get(name="New Reading List")
        assert reading_list.user == reading_list_user
        assert reading_list.attribution_source == ""  # Should be empty
        assert reading_list.attribution_url == ""  # Should be empty

    def test_create_view_admin_can_submit_attribution_fields(
        self, client, admin_user, test_password
    ):
        """Test that admin users can submit attribution fields."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:create")
        data = {
            "name": "Admin Reading List",
            "desc": "A reading list with attribution",
            "is_private": False,
            "list_type": ReadingList.ListType.EVENT,
            "attribution_source": ReadingList.AttributionSource.CBRO,
            "attribution_url": "https://example.com/source",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND
        # Check that the reading list was created WITH attribution data
        reading_list = ReadingList.objects.get(name="Admin Reading List")
        assert reading_list.user == admin_user
        assert reading_list.attribution_source == ReadingList.AttributionSource.CBRO
        assert reading_list.attribution_url == "https://example.com/source"

    def test_update_view_non_admin_cannot_see_attribution_fields(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Test that non-admin users don't see attribution fields in update form."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Attribution fields should not be in the form for non-admin users
        assert "attribution_source" not in form.fields
        assert "attribution_url" not in form.fields
        # Regular fields should still be present
        assert "name" in form.fields
        assert "desc" in form.fields
        assert "is_private" in form.fields

    def test_update_view_admin_can_see_attribution_fields(
        self, client, admin_user, metron_reading_list, test_password
    ):
        """Test that admin users see attribution fields in update form."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:update", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        form = resp.context["form"]
        # Admin users should see all fields including attribution fields
        assert "attribution_source" in form.fields
        assert "attribution_url" in form.fields
        assert "name" in form.fields
        assert "desc" in form.fields
        assert "is_private" in form.fields

    def test_update_view_non_admin_cannot_modify_attribution_fields(
        self, client, reading_list_user, test_password
    ):
        """Test that non-admin users cannot modify attribution fields."""
        # Create a reading list with attribution
        reading_list = ReadingList.objects.create(
            user=reading_list_user,
            name="List With Attribution",
            desc="Original description",
            is_private=False,
            attribution_source=ReadingList.AttributionSource.CBRO,
            attribution_url="https://example.com/original",
        )

        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:update", args=[reading_list.slug])
        data = {
            "name": "Updated List",
            "desc": "Updated description",
            "is_private": True,
            "list_type": ReadingList.ListType.EVENT,
            "attribution_source": ReadingList.AttributionSource.CMRO,  # Attempt to change
            "attribution_url": "https://example.com/modified",  # Attempt to change
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that regular fields were updated but attribution fields were NOT
        reading_list.refresh_from_db()
        assert reading_list.name == "Updated List"
        assert reading_list.desc == "Updated description"
        assert reading_list.is_private is True
        # Attribution should remain unchanged
        assert reading_list.attribution_source == ReadingList.AttributionSource.CBRO
        assert reading_list.attribution_url == "https://example.com/original"

    def test_update_view_admin_can_modify_attribution_fields(
        self, client, admin_user, metron_reading_list, test_password
    ):
        """Test that admin users can modify attribution fields."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:update", args=[metron_reading_list.slug])
        data = {
            "name": "Updated Metron List",
            "desc": "Updated description",
            "is_private": False,
            "list_type": ReadingList.ListType.EVENT,
            "attribution_source": ReadingList.AttributionSource.CMRO,
            "attribution_url": "https://example.com/updated",
        }
        resp = client.post(url, data)
        assert resp.status_code == HTTP_302_FOUND

        # Check that all fields including attribution were updated
        metron_reading_list.refresh_from_db()
        assert metron_reading_list.name == "Updated Metron List"
        assert metron_reading_list.desc == "Updated description"
        assert metron_reading_list.attribution_source == ReadingList.AttributionSource.CMRO
        assert metron_reading_list.attribution_url == "https://example.com/updated"
