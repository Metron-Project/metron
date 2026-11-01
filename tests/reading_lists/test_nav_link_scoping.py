"""Tests that reading list previous/next links are scoped to lists the user may access.

Linking a list also rewrites the linked list's reverse link (see ReadingList.save()),
so users may only link lists they can manage, and a linked list the viewer can't see
must not have its name or URL exposed.
"""

import pytest
from django.test import RequestFactory
from django.urls import reverse
from django.utils.html import escape
from rest_framework import status

from reading_lists.forms import ReadingListForm
from reading_lists.lookups import ReadingListLookup
from reading_lists.models import ReadingList

HTTP_200_OK = 200


@pytest.fixture
def other_user_private_list(other_user):
    """Create a private reading list owned by another user."""
    return ReadingList.objects.create(
        user=other_user,
        name="Secret Other List",
        desc="A private reading list owned by another user",
        is_private=True,
    )


@pytest.fixture
def public_list_linking_private(public_reading_list, other_user_private_list):
    """A public list whose next link points at another user's private list.

    Set with update() to model a link created before this scoping existed, without
    triggering ReadingList.save()'s reverse-link sync.
    """
    ReadingList.objects.filter(pk=public_reading_list.pk).update(next=other_user_private_list)
    public_reading_list.refresh_from_db()
    return public_reading_list


def _form_data(**links):
    return {"name": "Linked List", "list_type": ReadingList.ListType.EVENT, **links}


def _request_for(user):
    request = RequestFactory().get("/")
    request.user = user
    return request


class TestReadingListFormLinkScoping:
    def test_rejects_other_users_public_list(self, reading_list_user, other_user_reading_list):
        form = ReadingListForm(
            data=_form_data(next=other_user_reading_list.pk), user=reading_list_user
        )
        assert not form.is_valid()
        assert "next" in form.errors

    def test_rejects_other_users_private_list(self, reading_list_user, other_user_private_list):
        form = ReadingListForm(
            data=_form_data(previous=other_user_private_list.pk), user=reading_list_user
        )
        assert not form.is_valid()
        assert "previous" in form.errors

    def test_without_user_offers_no_lists(self, public_reading_list):
        form = ReadingListForm()
        assert not form.fields["previous"].queryset.exists()
        assert not form.fields["next"].queryset.exists()

    def test_regular_user_cannot_link_metron_list(self, reading_list_user, metron_reading_list):
        form = ReadingListForm(data=_form_data(next=metron_reading_list.pk), user=reading_list_user)
        assert not form.is_valid()
        assert "next" in form.errors

    def test_reading_list_editor_can_link_metron_list(
        self, reading_list_editor_user, metron_reading_list
    ):
        form = ReadingListForm(
            data=_form_data(next=metron_reading_list.pk), user=reading_list_editor_user
        )
        assert form.is_valid(), form.errors
        assert form.cleaned_data["next"] == metron_reading_list

    def test_existing_link_stays_valid_on_edit(
        self, reading_list_user, public_list_linking_private, other_user_private_list
    ):
        """A legacy link to another user's list doesn't block unrelated edits."""
        form = ReadingListForm(
            data=_form_data(next=other_user_private_list.pk),
            instance=public_list_linking_private,
            user=reading_list_user,
        )
        assert form.is_valid(), form.errors

    def test_rerendered_form_does_not_echo_disallowed_list_name(
        self, reading_list_user, other_user_private_list
    ):
        form = ReadingListForm(
            data=_form_data(previous=other_user_private_list.pk), user=reading_list_user
        )
        assert not form.is_valid()
        assert other_user_private_list.name not in str(form["previous"])

    def test_removing_selected_link_clears_it(
        self, reading_list_user, public_reading_list, private_reading_list
    ):
        public_reading_list.previous = private_reading_list
        public_reading_list.save()

        form = ReadingListForm(instance=public_reading_list, user=reading_list_user)
        assert private_reading_list.name in str(form["previous"])

        # A removed chip takes its hidden input with it, so the field is simply not submitted.
        form = ReadingListForm(
            data=_form_data(), instance=public_reading_list, user=reading_list_user
        )
        assert form.is_valid(), form.errors
        assert form.save().previous is None


class TestReadingListLookupScoping:
    def test_search_only_returns_users_own_lists(
        self,
        reading_list_user,
        public_reading_list,
        private_reading_list,
        other_user_reading_list,
        other_user_private_list,
    ):
        results = ReadingListLookup().search("List", _request_for(reading_list_user))
        assert set(results) == {public_reading_list, private_reading_list}

    def test_search_includes_metron_lists_for_editor(
        self, reading_list_editor_user, metron_reading_list, other_user_reading_list
    ):
        results = ReadingListLookup().search("List", _request_for(reading_list_editor_user))
        assert set(results) == {metron_reading_list}

    def test_labels_do_not_query_each_lists_owner(
        self,
        reading_list_user,
        public_reading_list,
        private_reading_list,
        django_assert_num_queries,
    ):
        lookup = ReadingListLookup()
        results = lookup.search("List", _request_for(reading_list_user))
        with django_assert_num_queries(1):
            items = [lookup.to_item(result) for result in results]
        assert len(items) == 2

    def test_search_endpoint_denies_anonymous_users(self, client, public_reading_list):
        url = reverse("izaya:search", args=["ReadingListLookup"])
        resp = client.get(url, {"q": "List"})
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert public_reading_list.name.encode() not in resp.content


class TestReadingListNavVisibility:
    def test_detail_hides_link_to_private_list_from_others(
        self, client, public_list_linking_private, other_user_private_list
    ):
        url = reverse("reading-list:detail", args=[public_list_linking_private.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["next_list"] is None
        assert escape(other_user_private_list.name).encode() not in resp.content
        assert other_user_private_list.get_absolute_url().encode() not in resp.content

    def test_detail_shows_link_to_private_list_to_its_owner(
        self,
        client,
        other_user,
        test_password,
        public_list_linking_private,
        other_user_private_list,
    ):
        client.login(username=other_user.username, password=test_password)
        url = reverse("reading-list:detail", args=[public_list_linking_private.slug])
        resp = client.get(url)
        assert resp.status_code == HTTP_200_OK
        assert resp.context["next_list"] == other_user_private_list
        assert escape(other_user_private_list.name).encode() in resp.content

    def test_api_hides_link_to_private_list_from_others(
        self, api_client_with_credentials, public_list_linking_private
    ):
        resp = api_client_with_credentials.get(
            reverse("api:reading_list-detail", kwargs={"pk": public_list_linking_private.pk})
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["next"] is None

    def test_api_shows_link_to_private_list_to_its_owner(
        self, api_client, other_user, public_list_linking_private, other_user_private_list
    ):
        api_client.force_authenticate(user=other_user)
        resp = api_client.get(
            reverse("api:reading_list-detail", kwargs={"pk": public_list_linking_private.pk})
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["next"] == {
            "id": other_user_private_list.pk,
            "name": other_user_private_list.name,
        }
