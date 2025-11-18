"""Tests for admin-only CBL import functionality."""

import tempfile
from pathlib import Path

from django.contrib.messages import get_messages
from django.urls import reverse

from reading_lists.models import ReadingList
from users.models import CustomUser

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403


class TestCBLImportAdminOnly:
    """Tests for CBL import restricted to admin users."""

    def test_cbl_import_view_anonymous(self, client):
        """Test that anonymous users cannot access CBL import."""
        url = reverse("reading-list:import")
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_cbl_import_view_regular_user(self, client, reading_list_user, test_password):
        """Test that regular users cannot access CBL import."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:import")
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_cbl_import_view_admin_user(self, client, admin_user, test_password):
        """Test that admin users can access CBL import."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:import")
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert "form" in resp.context
        assert resp.context["title"] == "Import Comic Book List"

    def test_cbl_import_result_view_regular_user(self, client, reading_list_user, test_password):
        """Test that regular users cannot access CBL import results."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:import-result")
        resp = client.get(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_cbl_import_result_view_admin_user(self, client, admin_user, test_password):
        """Test that admin users can access CBL import results (redirects if no session data)."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:import-result")
        resp = client.get(url)
        # Should redirect to my-lists if no import result in session
        assert resp.status_code == HTTP_302_FOUND
        assert "my-lists" in resp.url


class TestCBLImportAssignedToMetron:
    """Tests for CBL imports being assigned to Metron user."""

    def create_test_cbl_file(self, issue):
        """Helper to create a test CBL file."""
        year = issue.cover_date.year
        cbl_content = f"""<?xml version="1.0"?>
<ReadingList>
    <Name>Test Reading List</Name>
    <NumIssues>1</NumIssues>
    <Books>
        <Book Series="{issue.series.name}" Number="{issue.number}" Volume="1" Year="{year}">
            <Database Name="metron" Issue="{issue.id}" />
        </Book>
    </Books>
</ReadingList>"""

        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cbl", delete=False) as tmp_file:
            tmp_file.write(cbl_content)
            return Path(tmp_file.name)

    def test_cbl_import_assigned_to_metron_user(
        self, client, admin_user, metron_user, reading_list_issue_1, test_password
    ):
        """Test that CBL imports are assigned to the Metron user."""
        client.login(username=admin_user.username, password=test_password)

        # Create a test CBL file
        cbl_file_path = self.create_test_cbl_file(reading_list_issue_1)

        try:
            url = reverse("reading-list:import")
            with cbl_file_path.open("rb") as f:
                data = {
                    "cbl_file": f,
                    "is_private": False,
                    "attribution_source": "CBRO",
                    "attribution_url": "https://example.com",
                }
                resp = client.post(url, data)

            assert resp.status_code == HTTP_302_FOUND

            # Check that the reading list was created for Metron user
            reading_list = ReadingList.objects.get(name="Test Reading List")
            assert reading_list.user == metron_user
            assert reading_list.user.username == "Metron"
            assert not reading_list.is_private
            assert reading_list.attribution_source == "CBRO"
            assert reading_list.attribution_url == "https://example.com"

        finally:
            # Clean up the temporary file
            if cbl_file_path.exists():
                cbl_file_path.unlink()

    def test_cbl_import_without_metron_user(
        self, client, admin_user, reading_list_issue_1, test_password
    ):
        """Test that CBL import fails gracefully if Metron user doesn't exist."""
        # Note: This test will only work if metron_user fixture is not loaded
        # In practice, the metron_user should always exist, but this tests the error handling
        client.login(username=admin_user.username, password=test_password)

        # Delete Metron user if it exists (for this test)
        CustomUser.objects.filter(username="Metron").delete()

        # Create a test CBL file
        cbl_file_path = self.create_test_cbl_file(reading_list_issue_1)

        try:
            url = reverse("reading-list:import")
            with cbl_file_path.open("rb") as f:
                data = {
                    "cbl_file": f,
                    "is_private": False,
                }
                resp = client.post(url, data)

            # Should return to form with error message
            assert resp.status_code == HTTP_200_OK

            # Check for error message
            messages = list(get_messages(resp.wsgi_request))
            assert any("Metron" in str(m) and "does not exist" in str(m) for m in messages)

        finally:
            # Clean up the temporary file
            if cbl_file_path.exists():
                cbl_file_path.unlink()

    def test_cbl_import_creates_private_list_for_metron(
        self, client, admin_user, metron_user, reading_list_issue_1, test_password
    ):
        """Test that CBL imports can create private lists for Metron."""
        client.login(username=admin_user.username, password=test_password)

        # Create a test CBL file
        cbl_file_path = self.create_test_cbl_file(reading_list_issue_1)

        try:
            url = reverse("reading-list:import")
            with cbl_file_path.open("rb") as f:
                data = {
                    "cbl_file": f,
                    "is_private": True,  # Create as private
                }
                resp = client.post(url, data)

            assert resp.status_code == HTTP_302_FOUND

            # Check that the reading list was created as private for Metron user
            reading_list = ReadingList.objects.get(name="Test Reading List")
            assert reading_list.user == metron_user
            assert reading_list.is_private

        finally:
            # Clean up the temporary file
            if cbl_file_path.exists():
                cbl_file_path.unlink()

    def test_cbl_import_duplicate_name_for_metron(
        self, client, admin_user, metron_user, reading_list_issue_1, test_password
    ):
        """Test that duplicate CBL imports for Metron are rejected."""
        client.login(username=admin_user.username, password=test_password)

        # Create a reading list with the same name for Metron
        ReadingList.objects.create(
            user=metron_user,
            name="Test Reading List",
            is_private=False,
        )

        # Create a test CBL file
        cbl_file_path = self.create_test_cbl_file(reading_list_issue_1)

        try:
            url = reverse("reading-list:import")
            with cbl_file_path.open("rb") as f:
                data = {
                    "cbl_file": f,
                    "is_private": False,
                }
                resp = client.post(url, data)

            # Should return to form with error message
            assert resp.status_code == HTTP_200_OK

            # Check for error message about duplicate
            messages = list(get_messages(resp.wsgi_request))
            assert any("already exists" in str(m) for m in messages)

        finally:
            # Clean up the temporary file
            if cbl_file_path.exists():
                cbl_file_path.unlink()
