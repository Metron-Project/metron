import pytest
from django.urls import reverse
from django.utils.text import slugify
from pytest_django.asserts import assertTemplateUsed

from comicsdb.models.attribution import Attribution
from comicsdb.models.team import Team

HTML_OK_CODE = 200
HTML_REDIRECT_CODE = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_series(create_user):
    user = create_user()
    for pub_num in range(PAGINATE_TEST_VAL):
        Team.objects.create(
            name=f"Team {pub_num}", slug=f"team-{pub_num}", edited_by=user, created_by=user
        )


def test_team_detail(avengers, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/team/{avengers.slug}/")
    assert resp.status_code == HTML_OK_CODE


def test_team_redirect(avengers, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/team/{avengers.pk}/")
    assert resp.status_code == HTML_REDIRECT_CODE


def test_team_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/team/search")
    assert resp.status_code == HTML_OK_CODE


def test_team_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("team:search"))
    assert resp.status_code == HTML_OK_CODE


def test_team_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("team:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/team_list.html")


def test_team_search_pagination_is_thirty(auto_login_user, list_of_series):
    client, _ = auto_login_user()
    resp = client.get("/team/search?q=tea")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["team_list"]) == PAGINATE_DEFAULT_VAL


def test_team_search_lists_all_teams(auto_login_user, list_of_series):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get("/team/search?page=2&q=tea")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["team_list"]) == PAGINATE_DIFF_VAL


def test_team_list_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/team/")
    assert resp.status_code == HTML_OK_CODE


def test_team_list_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("team:list"))
    assert resp.status_code == HTML_OK_CODE


def test_team_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("team:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/team_list.html")


def test_team_list_pagination_is_thirty(auto_login_user, list_of_series):
    client, _ = auto_login_user()
    resp = client.get(reverse("team:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["team_list"]) == PAGINATE_DEFAULT_VAL


def test_team_lists_second_page(auto_login_user, list_of_series):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("team:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["team_list"]) == PAGINATE_DIFF_VAL


# CreateView
def test_create_team_validform_view(auto_login_user, teen_titans):
    team_name = "U-Foes"
    team_slug = slugify(team_name)
    data = {
        "name": team_name,
        "slug": team_slug,
        "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
        "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
        "comicsdb-attribution-content_type-object_id-0-source": "W",
        "comicsdb-attribution-content_type-object_id-0-url": "https://en.wikipedia.org/wiki/U_Foes",
    }
    client, _ = auto_login_user()
    team_count = Team.objects.count()
    resp = client.post(reverse("team:create"), data=data)
    uf = Team.objects.get(slug=team_slug)
    assert resp.status_code == 302
    assert Team.objects.count() == team_count + 1
    assert Attribution.objects.count() == 1
    assert uf.name == team_name
    assert uf.slug == team_slug


# UpdateView
def test_team_update_view(auto_login_user, teen_titans):
    client, _ = auto_login_user()
    k = {"slug": teen_titans.slug}
    resp = client.get(reverse("team:update", kwargs=k))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/model_with_attribution_form.html")


# def test_team_update_form(auto_login_user, teen_titans):
#     data = {
#         "name": "Teen Titans",
#         "slug": "teen-titans",
#         "desc": "The sidekicks",
#         "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
#         "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
#         "comicsdb-attribution-content_type-object_id-0-source": "W",
#         "comicsdb-attribution-content_type-object_id-0-url": "https://en.wikipedia.org/wiki/Teen_Titans",
#     }
#     client, _ = auto_login_user()
#     k = {"slug": teen_titans.slug}
#     team_count = Team.objects.count()
#     client.post(reverse("team:update", kwargs=k), data=data)
#     # assert resp.status_code == 302
#     assert Team.objects.count() == team_count
#     tt = Team.objects.get(slug="teen-titans")
#     tt.desc == "The sidekicks"
#     # assert Attribution.objects.count() == 1


# Team History Views
def test_team_history_view_requires_login(client, teen_titans):
    """Test that history view requires authentication."""
    resp = client.get(reverse("team:history", kwargs={"slug": teen_titans.slug}))
    assert resp.status_code == HTML_REDIRECT_CODE


def test_team_history_view_accessible(auto_login_user, teen_titans):
    """Test that history view is accessible by name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("team:history", kwargs={"slug": teen_titans.slug}))
    assert resp.status_code == HTML_OK_CODE


def test_team_history_uses_correct_template(auto_login_user, teen_titans):
    """Test that history view uses the correct template."""
    client, _ = auto_login_user()
    resp = client.get(reverse("team:history", kwargs={"slug": teen_titans.slug}))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/history_list.html")


def test_team_history_shows_creation(auto_login_user, teen_titans):
    """Test that history shows the initial creation record."""
    client, _ = auto_login_user()
    resp = client.get(reverse("team:history", kwargs={"slug": teen_titans.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "history_list" in resp.context
    assert len(resp.context["history_list"]) >= 1


def test_team_history_context(auto_login_user, teen_titans):
    """Test that history view context includes object and model name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("team:history", kwargs={"slug": teen_titans.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "object" in resp.context
    assert resp.context["object"] == teen_titans
    assert "model_name" in resp.context
    assert resp.context["model_name"] == "team"
