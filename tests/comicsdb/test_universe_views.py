import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from comicsdb.models import Universe

HTML_OK_CODE = 200
HTML_REDIRECT_CODE = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_universes(create_user, dc_comics):
    user = create_user()
    for uni_num in range(PAGINATE_TEST_VAL):
        Universe.objects.create(
            publisher=dc_comics,
            name=f"Test Universe {uni_num}",
            slug=f"test-universe-{uni_num}",
            edited_by=user,
            created_by=user,
        )


def test_universe_detail(earth_2_universe, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/universe/{earth_2_universe.slug}/")
    assert resp.status_code == HTML_OK_CODE


def test_universe_redirect(earth_2_universe, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/universe/{earth_2_universe.pk}/")
    assert resp.status_code == HTML_REDIRECT_CODE


def test_universe_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/universe/search")
    assert resp.status_code == HTML_OK_CODE


def test_universe_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:search"))
    assert resp.status_code == HTML_OK_CODE


def test_universe_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/universe_list.html")


def test_universe_search_pagination_is_thirty(auto_login_user, list_of_universes):
    client, _ = auto_login_user()
    resp = client.get("/universe/search?q=test")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["universe_list"]) == PAGINATE_DEFAULT_VAL


def test_universe_search_lists_all_universes(auto_login_user, list_of_universes):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get("/universe/search?page=2&q=test")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["universe_list"]) == PAGINATE_DIFF_VAL


def test_universe_list_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/universe/")
    assert resp.status_code == HTML_OK_CODE


def test_universe_list_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:list"))
    assert resp.status_code == HTML_OK_CODE


def test_universe_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/universe_list.html")


def test_universe_list_pagination_is_thirty(auto_login_user, list_of_universes):
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["universe_list"]) == PAGINATE_DEFAULT_VAL


def test_universe_list_second_page(auto_login_user, list_of_universes):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["universe_list"]) == PAGINATE_DIFF_VAL


# Universe History Views
def test_universe_history_view_requires_login(client, earth_2_universe):
    """Test that history view requires authentication."""
    resp = client.get(reverse("universe:history", kwargs={"slug": earth_2_universe.slug}))
    assert resp.status_code == HTML_REDIRECT_CODE


def test_universe_history_view_accessible(auto_login_user, earth_2_universe):
    """Test that history view is accessible by name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:history", kwargs={"slug": earth_2_universe.slug}))
    assert resp.status_code == HTML_OK_CODE


def test_universe_history_uses_correct_template(auto_login_user, earth_2_universe):
    """Test that history view uses the correct template."""
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:history", kwargs={"slug": earth_2_universe.slug}))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/history_list.html")


def test_universe_history_shows_creation(auto_login_user, earth_2_universe):
    """Test that history shows the initial creation record."""
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:history", kwargs={"slug": earth_2_universe.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "history_list" in resp.context
    assert len(resp.context["history_list"]) >= 1


def test_universe_history_context(auto_login_user, earth_2_universe):
    """Test that history view context includes object and model name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("universe:history", kwargs={"slug": earth_2_universe.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "object" in resp.context
    assert resp.context["object"] == earth_2_universe
    assert "model_name" in resp.context
    assert resp.context["model_name"] == "universe"
