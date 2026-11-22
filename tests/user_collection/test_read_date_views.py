"""Tests for adding and deleting collection item read dates."""

from datetime import UTC, datetime

from django.urls import reverse
from django.utils import timezone as django_timezone

from user_collection.models import ReadDate

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_404_NOT_FOUND = 404


class TestAddReadDateView:
    """Tests for the add_read_date HTMX view."""

    def test_add_read_date_requires_login(self, client, collection_item):
        """Test that the view requires login."""
        url = reverse("user_collection:add_read_date", kwargs={"pk": collection_item.pk})
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_add_read_date_requires_post(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that the view requires POST method."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add_read_date", kwargs={"pk": collection_item.pk})
        resp = client.get(url)
        # Should return 405 Method Not Allowed
        assert resp.status_code == 405

    def test_add_read_date_without_date(
        self, client, collection_user, collection_item, test_password
    ):
        """Test adding a read date without specifying a date (uses current time)."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add_read_date", kwargs={"pk": collection_item.pk})

        before_time = django_timezone.now()
        resp = client.post(url, {}, HTTP_HX_REQUEST="true")
        after_time = django_timezone.now()

        assert resp.status_code == HTTP_200_OK
        assert collection_item.read_dates.count() == 1

        read_date = collection_item.read_dates.first().read_date
        assert before_time <= read_date <= after_time

        # Check backward compatibility fields were synced
        collection_item.refresh_from_db()
        assert collection_item.is_read is True
        assert collection_item.date_read == read_date

    def test_add_read_date_with_specific_date(
        self, client, collection_user, collection_item, test_password
    ):
        """Test adding a read date with a specific date and time."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add_read_date", kwargs={"pk": collection_item.pk})

        # Bulma Calendar format: yyyy-MM-dd HH:mm
        resp = client.post(
            url,
            {"read_date": "2024-06-15 14:30"},
            HTTP_HX_REQUEST="true",
        )

        assert resp.status_code == HTTP_200_OK
        assert collection_item.read_dates.count() == 1

        # Verify the read date was created
        assert collection_item.read_dates.exists()
        # Check backward compat fields were updated
        collection_item.refresh_from_db()
        assert collection_item.is_read is True
        assert collection_item.date_read is not None

    def test_add_multiple_read_dates(self, client, collection_user, collection_item, test_password):
        """Test adding multiple read dates to the same item."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add_read_date", kwargs={"pk": collection_item.pk})

        # Add first read date
        client.post(url, {"read_date": "2024-01-15 10:00"}, HTTP_HX_REQUEST="true")
        assert collection_item.read_dates.count() == 1

        # Add second read date
        client.post(url, {"read_date": "2024-06-15 14:30"}, HTTP_HX_REQUEST="true")
        assert collection_item.read_dates.count() == 2

        # Add third read date
        client.post(url, {}, HTTP_HX_REQUEST="true")
        assert collection_item.read_dates.count() == 3

    def test_add_read_date_other_users_item(
        self, client, collection_user, other_collection_user, collection_item, test_password
    ):
        """Test that users cannot add read dates to other users' items."""
        # collection_item belongs to collection_user
        client.login(username=other_collection_user.username, password=test_password)
        url = reverse("user_collection:add_read_date", kwargs={"pk": collection_item.pk})

        resp = client.post(url, {}, HTTP_HX_REQUEST="true")
        assert resp.status_code == HTTP_404_NOT_FOUND
        assert collection_item.read_dates.count() == 0

    def test_add_read_date_invalid_format(
        self, client, collection_user, collection_item, test_password
    ):
        """Test adding a read date with invalid date format falls back to current time."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse("user_collection:add_read_date", kwargs={"pk": collection_item.pk})

        before_time = django_timezone.now()
        resp = client.post(
            url,
            {"read_date": "invalid-date"},
            HTTP_HX_REQUEST="true",
        )
        after_time = django_timezone.now()

        assert resp.status_code == HTTP_200_OK
        assert collection_item.read_dates.count() == 1

        # Should have fallen back to current time
        read_date = collection_item.read_dates.first().read_date
        assert before_time <= read_date <= after_time


class TestDeleteReadDateView:
    """Tests for the delete_read_date HTMX view."""

    def test_delete_read_date_requires_login(self, client, collection_item):
        """Test that the view requires login."""
        read_date = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=django_timezone.now(),
        )
        url = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": read_date.pk},
        )
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_delete_read_date_requires_post(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that the view requires POST method."""
        read_date = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=django_timezone.now(),
        )
        client.login(username=collection_user.username, password=test_password)
        url = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": read_date.pk},
        )
        resp = client.get(url)
        assert resp.status_code == 405

    def test_delete_read_date_success(
        self, client, collection_user, collection_item, test_password
    ):
        """Test successfully deleting a read date."""
        read_date = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=django_timezone.now(),
        )
        client.login(username=collection_user.username, password=test_password)
        url = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": read_date.pk},
        )

        assert collection_item.read_dates.count() == 1
        resp = client.post(url, HTTP_HX_REQUEST="true")

        assert resp.status_code == HTTP_200_OK
        assert collection_item.read_dates.count() == 0

    def test_delete_read_date_updates_backward_compat_fields(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that deleting the last read date updates is_read and date_read."""
        read_date = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
        )

        # Sync backward compatibility fields
        collection_item.is_read = True
        collection_item.date_read = read_date.read_date
        collection_item.save()

        client.login(username=collection_user.username, password=test_password)
        url = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": read_date.pk},
        )

        resp = client.post(url, HTTP_HX_REQUEST="true")
        assert resp.status_code == HTTP_200_OK

        collection_item.refresh_from_db()
        assert collection_item.is_read is False
        assert collection_item.date_read is None

    def test_delete_one_of_multiple_read_dates(
        self, client, collection_user, collection_item, test_password
    ):
        """Test deleting one read date when multiple exist."""
        date1 = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        )
        date2 = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
        )

        client.login(username=collection_user.username, password=test_password)
        url = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": date1.pk},
        )

        assert collection_item.read_dates.count() == 2
        resp = client.post(url, HTTP_HX_REQUEST="true")

        assert resp.status_code == HTTP_200_OK
        assert collection_item.read_dates.count() == 1
        assert collection_item.read_dates.first() == date2

        # Backward compat fields should still show read with latest date
        collection_item.refresh_from_db()
        assert collection_item.is_read is True
        assert collection_item.date_read == date2.read_date

    def test_delete_read_date_other_users_item(
        self, client, collection_user, other_collection_user, collection_item, test_password
    ):
        """Test that users cannot delete read dates from other users' items."""
        read_date = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=django_timezone.now(),
        )

        # collection_item belongs to collection_user
        client.login(username=other_collection_user.username, password=test_password)
        url = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": read_date.pk},
        )

        resp = client.post(url, HTTP_HX_REQUEST="true")
        assert resp.status_code == HTTP_404_NOT_FOUND
        assert collection_item.read_dates.count() == 1

    def test_delete_nonexistent_read_date(
        self, client, collection_user, collection_item, test_password
    ):
        """Test deleting a read date that doesn't exist."""
        client.login(username=collection_user.username, password=test_password)
        url = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": 99999},
        )

        resp = client.post(url, HTTP_HX_REQUEST="true")
        assert resp.status_code == HTTP_404_NOT_FOUND

    def test_delete_multiple_read_dates_sequentially(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that multiple read dates can be deleted in sequence.

        This verifies that deleting one read date doesn't prevent deleting another,
        which could happen if the HTMX response doesn't properly reinitialize
        the UI components for the remaining read dates.
        """
        date1 = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        )
        date2 = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=datetime(2024, 3, 20, 14, 0, 0, tzinfo=UTC),
        )
        date3 = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=datetime(2024, 6, 15, 18, 30, 0, tzinfo=UTC),
        )

        client.login(username=collection_user.username, password=test_password)

        # Verify initial state
        assert collection_item.read_dates.count() == 3

        # Delete the first read date
        url1 = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": date1.pk},
        )
        resp1 = client.post(url1, HTTP_HX_REQUEST="true")
        assert resp1.status_code == HTTP_200_OK
        assert collection_item.read_dates.count() == 2

        # Delete the second read date - this should work even after the first deletion
        url2 = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": date2.pk},
        )
        resp2 = client.post(url2, HTTP_HX_REQUEST="true")
        assert resp2.status_code == HTTP_200_OK
        assert collection_item.read_dates.count() == 1

        # Delete the last read date
        url3 = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": date3.pk},
        )
        resp3 = client.post(url3, HTTP_HX_REQUEST="true")
        assert resp3.status_code == HTTP_200_OK
        assert collection_item.read_dates.count() == 0

        # Verify backward compat fields are updated correctly
        collection_item.refresh_from_db()
        assert collection_item.is_read is False
        assert collection_item.date_read is None

    def test_delete_read_date_response_contains_remaining_dates(
        self, client, collection_user, collection_item, test_password
    ):
        """Test that the response after deletion contains the remaining read dates.

        The HTMX response should include the updated list of read dates so the
        UI can be properly updated with working delete buttons for remaining dates.
        """
        date1 = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        )
        date2 = ReadDate.objects.create(
            collection_item=collection_item,
            read_date=datetime(2024, 6, 15, 14, 30, 0, tzinfo=UTC),
        )

        client.login(username=collection_user.username, password=test_password)

        # Delete the first read date
        url = reverse(
            "user_collection:delete_read_date",
            kwargs={"pk": collection_item.pk, "read_date_pk": date1.pk},
        )
        resp = client.post(url, HTTP_HX_REQUEST="true")

        assert resp.status_code == HTTP_200_OK
        content = resp.content.decode()

        # Verify the response contains the remaining read date's delete button/modal
        assert f"delete-read-date-modal-{date2.pk}" in content
        # Verify the deleted read date's modal is no longer present
        assert f"delete-read-date-modal-{date1.pk}" not in content
        # Verify the remaining date is displayed
        assert "June 15, 2024" in content
