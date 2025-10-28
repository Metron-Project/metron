import pytest
from django.urls import reverse
from django.utils.text import slugify
from pytest_django.asserts import assertTemplateUsed

from comicsdb.models import Creator
from comicsdb.models.attribution import Attribution

HTML_OK_CODE = 200
HTML_REDIRECT_CODE = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_creators(create_user):
    user = create_user()
    for pub_num in range(PAGINATE_TEST_VAL):
        Creator.objects.create(
            name=f"John-Smith-{pub_num}",
            slug=f"john-smith-{pub_num}",
            edited_by=user,
            created_by=user,
        )


def test_creator_detail(walter_simonson, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/creator/{walter_simonson.slug}/")
    assert resp.status_code == HTML_OK_CODE


def test_creator_redirect(walter_simonson, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/creator/{walter_simonson.pk}/")
    assert resp.status_code == HTML_REDIRECT_CODE


# Creator Views
def test_update_view_url_accessible_by_name(auto_login_user, john_byrne):
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:update", kwargs={"slug": john_byrne.slug}))
    assert resp.status_code == HTML_OK_CODE


# def test_creator_update_view(auto_login_user, john_byrne):
#     client, user = auto_login_user()
#     new_name = "JB"
#     resp = client.post(
#         reverse("creator:update", kwargs={"slug": john_byrne.slug}),
#         {"name": new_name, "slug": john_byrne.slug, "edited_by": user},
#     )
#     assert resp.status_code == HTML_REDIRECT_CODE
#     john_byrne.refresh_from_db()
#     assert john_byrne.name == new_name


# Create View
def test_creator_create_view(auto_login_user, walter_simonson):
    name = "Jack Kirby"
    slug = slugify(name)
    client, user = auto_login_user()
    data = {
        "name": name,
        "slug": slug,
        "edited_by": user,
        "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
        "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
        "comicsdb-attribution-content_type-object_id-0-source": "W",
        "comicsdb-attribution-content_type-object_id-0-url": "https://en.wikipedia.org/wiki/Jack_Kirby",
    }
    creator_count = Creator.objects.count()
    resp = client.post(reverse("creator:create"), data=data)
    jack = Creator.objects.get(slug=slug)
    assert resp.status_code == HTML_REDIRECT_CODE
    assert Creator.objects.count() == creator_count + 1
    assert Attribution.objects.count() == 1
    assert jack is not None
    assert jack.name == name


# Creator Search
def test_creator_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/creator/search")
    assert resp.status_code == HTML_OK_CODE


def test_creator_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:search"))
    assert resp.status_code == HTML_OK_CODE


def test_creator_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/creator_list.html")


def test_creator_search_pagination_is_thirty(auto_login_user, list_of_creators):
    client, _ = auto_login_user()
    resp = client.get("/creator/search?q=smith")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["creator_list"]) == PAGINATE_DEFAULT_VAL


def test_creator_search_lists_all_creators(auto_login_user, list_of_creators):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get("/creator/search?page=2&q=smith")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["creator_list"]) == PAGINATE_DIFF_VAL


# CreatorList
def test_creator_list_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/creator/")
    assert resp.status_code == HTML_OK_CODE


def test_creator_list_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:list"))
    assert resp.status_code == HTML_OK_CODE


def test_creator_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/creator_list.html")


def test_creator_list_pagination_is_thirty(auto_login_user, list_of_creators):
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["creator_list"]) == PAGINATE_DEFAULT_VAL


def test_creator_list_lists_second_page(auto_login_user, list_of_creators):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["creator_list"]) == PAGINATE_DIFF_VAL


# Creator History Views
def test_creator_history_view_requires_login(client, john_byrne):
    """Test that history view requires authentication."""
    resp = client.get(reverse("creator:history", kwargs={"slug": john_byrne.slug}))
    assert resp.status_code == HTML_REDIRECT_CODE


def test_creator_history_view_accessible(auto_login_user, john_byrne):
    """Test that history view is accessible by name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:history", kwargs={"slug": john_byrne.slug}))
    assert resp.status_code == HTML_OK_CODE


def test_creator_history_uses_correct_template(auto_login_user, john_byrne):
    """Test that history view uses the correct template."""
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:history", kwargs={"slug": john_byrne.slug}))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/history_list.html")


def test_creator_history_shows_creation(auto_login_user, john_byrne):
    """Test that history shows the initial creation record."""
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:history", kwargs={"slug": john_byrne.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "history_list" in resp.context
    assert len(resp.context["history_list"]) >= 1


def test_creator_history_context(auto_login_user, john_byrne):
    """Test that history view context includes object and model name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("creator:history", kwargs={"slug": john_byrne.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "object" in resp.context
    assert resp.context["object"] == john_byrne
    assert "model_name" in resp.context
    assert resp.context["model_name"] == "creator"
