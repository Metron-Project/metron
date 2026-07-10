"""Tests for reassigning a reading list's owner to the Metron account."""

from django.urls import reverse

from reading_lists.views import can_assign_reading_list_to_metron

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403


class TestAssignReadingListToMetron:
    """Tests for the 'assign to Metron' ownership-transfer action."""

    def test_editor_can_view_confirm_page(
        self, client, reading_list_editor_user, public_reading_list, test_password
    ):
        """Reading list editors can view the confirm page for another user's list."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:assign-to-metron", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["reading_list"] == public_reading_list

    def test_editor_can_assign_other_user_list_to_metron(
        self,
        client,
        reading_list_editor_user,
        public_reading_list,
        metron_user,
        test_password,
    ):
        """Reading list editors can reassign another user's list to Metron."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:assign-to-metron", args=[public_reading_list.slug])
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        public_reading_list.refresh_from_db()
        assert public_reading_list.user == metron_user

    def test_staff_can_assign_other_user_list_to_metron(
        self,
        client,
        admin_user,
        public_reading_list,
        metron_user,
        test_password,
    ):
        """Staff (not necessarily in the editor group) can reassign lists to Metron."""
        client.login(username=admin_user.username, password=test_password)
        url = reverse("reading-list:assign-to-metron", args=[public_reading_list.slug])
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        public_reading_list.refresh_from_db()
        assert public_reading_list.user == metron_user

    def test_regular_user_cannot_assign_list_to_metron(
        self, client, other_user, public_reading_list, test_password
    ):
        """A regular authenticated user without staff/editor status is forbidden."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:assign-to-metron", args=[public_reading_list.slug])
        resp = client.post(url)
        assert resp.status_code == HTTP_403_FORBIDDEN
        public_reading_list.refresh_from_db()
        assert public_reading_list.user.username != "Metron"

    def test_owner_without_editor_group_cannot_assign_own_list(
        self, client, reading_list_user, public_reading_list, test_password
    ):
        """Owning the list alone does not grant permission to reassign it to Metron."""
        client.login(username=reading_list_user.username, password=test_password)
        url = reverse("reading-list:assign-to-metron", args=[public_reading_list.slug])
        resp = client.post(url)
        assert resp.status_code == HTTP_403_FORBIDDEN

    def test_anonymous_user_redirected_to_login(self, client, public_reading_list):
        """Anonymous users are redirected to login."""
        url = reverse("reading-list:assign-to-metron", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp.url

    def test_get_redirects_when_already_owned_by_metron(
        self, client, reading_list_editor_user, metron_reading_list, test_password
    ):
        """The confirm page redirects if the list is already owned by Metron."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:assign-to-metron", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_302_FOUND
        assert resp.url == metron_reading_list.get_absolute_url()

    def test_post_is_noop_when_already_owned_by_metron(
        self, client, reading_list_editor_user, metron_reading_list, metron_user, test_password
    ):
        """Posting on an already-Metron-owned list leaves the owner unchanged."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:assign-to-metron", args=[metron_reading_list.slug])
        resp = client.post(url)
        assert resp.status_code == HTTP_302_FOUND
        metron_reading_list.refresh_from_db()
        assert metron_reading_list.user == metron_user

    def test_detail_view_shows_button_for_editor_on_other_user_list(
        self, client, reading_list_editor_user, public_reading_list, test_password
    ):
        """The detail view context flags the action as available for editors."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["can_assign_to_metron"] is True
        assert b"Assign to Metron" in resp.content

    def test_detail_view_hides_button_for_regular_user(
        self, client, other_user, public_reading_list, test_password
    ):
        """The detail view hides the action for users without staff/editor status."""
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[public_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["can_assign_to_metron"] is False
        assert b"Assign to Metron" not in resp.content

    def test_detail_view_hides_button_when_already_metron_owned(
        self, client, reading_list_editor_user, metron_reading_list, test_password
    ):
        """The detail view hides the action once the list is already Metron-owned."""
        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[metron_reading_list.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["can_assign_to_metron"] is False

    def test_missing_metron_user_shows_error(
        self, client, reading_list_editor_user, public_reading_list, metron_user, test_password
    ):
        """If the Metron account doesn't exist, the POST fails gracefully."""
        metron_user.username = "not-metron"
        metron_user.save()

        client.login(username=reading_list_editor_user.username, password=test_password)
        url = reverse("reading-list:assign-to-metron", args=[public_reading_list.slug])
        resp = client.post(url, follow=True)
        assert resp.status_code == HTTP_200_OK
        messages = list(resp.context["messages"])
        assert any("does not exist" in str(m) for m in messages)
        public_reading_list.refresh_from_db()
        assert public_reading_list.user.username != "not-metron"


class TestCanAssignReadingListToMetronHelper:
    """Direct tests for the permission helper function."""

    def test_staff_user_can_assign(self, admin_user):
        assert can_assign_reading_list_to_metron(admin_user) is True

    def test_editor_group_user_can_assign(self, reading_list_editor_user):
        assert can_assign_reading_list_to_metron(reading_list_editor_user) is True

    def test_regular_user_cannot_assign(self, other_user):
        assert can_assign_reading_list_to_metron(other_user) is False
