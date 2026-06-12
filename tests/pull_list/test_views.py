"""Tests for pull_list views."""

from django.urls import reverse

from pull_list.models import PullList, PullListSeries


# Toggle view
def test_toggle_requires_login(client, pull_list_series):
    resp = client.post(reverse("pull-list:toggle", kwargs={"slug": pull_list_series.slug}))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


def test_toggle_get_not_allowed(client, pull_list_user, test_password, pull_list_series):
    client.login(username=pull_list_user.username, password=test_password)
    resp = client.get(reverse("pull-list:toggle", kwargs={"slug": pull_list_series.slug}))
    assert resp.status_code == 405


def test_toggle_adds_series_to_pull_list(client, pull_list_user, test_password, pull_list_series):
    client.login(username=pull_list_user.username, password=test_password)
    resp = client.post(reverse("pull-list:toggle", kwargs={"slug": pull_list_series.slug}))
    assert resp.status_code == 200
    assert PullListSeries.objects.filter(
        pull_list__user=pull_list_user, series=pull_list_series
    ).exists()


def test_toggle_removes_series_from_pull_list(
    client, pull_list_user, test_password, pull_list_with_series, pull_list_series
):
    client.login(username=pull_list_user.username, password=test_password)
    resp = client.post(reverse("pull-list:toggle", kwargs={"slug": pull_list_series.slug}))
    assert resp.status_code == 200
    assert not PullListSeries.objects.filter(
        pull_list__user=pull_list_user, series=pull_list_series
    ).exists()


def test_toggle_response_contains_button(client, pull_list_user, test_password, pull_list_series):
    client.login(username=pull_list_user.username, password=test_password)
    resp = client.post(reverse("pull-list:toggle", kwargs={"slug": pull_list_series.slug}))
    assert resp.status_code == 200
    assert b"pull-list-btn" in resp.content


def test_toggle_creates_pull_list_if_missing(
    client, pull_list_user, test_password, pull_list_series
):
    client.login(username=pull_list_user.username, password=test_password)
    assert not PullList.objects.filter(user=pull_list_user).exists()
    client.post(reverse("pull-list:toggle", kwargs={"slug": pull_list_series.slug}))
    assert PullList.objects.filter(user=pull_list_user).exists()


# Detail view — authentication
def test_detail_view_requires_login(client):
    resp = client.get(reverse("pull-list:detail"))
    assert resp.status_code == 302
    assert "/accounts/login" in resp["Location"]


def test_detail_view_authenticated_creates_pull_list(client, pull_list_user, test_password):
    client.login(username=pull_list_user.username, password=test_password)
    assert not PullList.objects.filter(user=pull_list_user).exists()
    resp = client.get(reverse("pull-list:detail"))
    assert resp.status_code == 200
    assert PullList.objects.filter(user=pull_list_user).exists()


def test_detail_view_shows_series_on_list(
    client, pull_list_user, test_password, pull_list_with_series, pull_list_series
):
    client.login(username=pull_list_user.username, password=test_password)
    resp = client.get(reverse("pull-list:detail"))
    assert resp.status_code == 200
    assert pull_list_series.name in resp.content.decode()


# Add series via POST
def test_add_series_to_pull_list(
    client, pull_list_user, test_password, pull_list, pull_list_series
):
    client.login(username=pull_list_user.username, password=test_password)
    resp = client.post(
        reverse("pull-list:detail"),
        data={"series": pull_list_series.pk},
    )
    assert resp.status_code == 302
    assert PullListSeries.objects.filter(pull_list=pull_list, series=pull_list_series).exists()


def test_add_duplicate_series_shows_info_message(
    client, pull_list_user, test_password, pull_list_with_series, pull_list_series
):
    client.login(username=pull_list_user.username, password=test_password)
    resp = client.post(
        reverse("pull-list:detail"),
        data={"series": pull_list_series.pk},
        follow=True,
    )
    assert resp.status_code == 200
    assert (
        PullListSeries.objects.filter(
            pull_list=pull_list_with_series, series=pull_list_series
        ).count()
        == 1
    )


# Remove series view
def test_remove_series_requires_login(client, pull_list_with_series, pull_list_series):
    resp = client.get(reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk}))
    assert resp.status_code == 302


def test_remove_series_owner_can_remove(
    client, pull_list_user, test_password, pull_list_with_series, pull_list_series
):
    client.login(username=pull_list_user.username, password=test_password)
    resp = client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk})
    )
    assert resp.status_code == 302
    assert not PullListSeries.objects.filter(
        pull_list=pull_list_with_series, series=pull_list_series
    ).exists()


def test_remove_series_other_user_cannot_remove(
    client, other_pull_list_user, test_password, pull_list_with_series, pull_list_series
):
    client.login(username=other_pull_list_user.username, password=test_password)
    resp = client.post(
        reverse("pull-list:remove-series", kwargs={"series_pk": pull_list_series.pk})
    )
    assert resp.status_code in (403, 404)
