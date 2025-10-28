import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from comicsdb.forms.arc import ArcForm
from comicsdb.models.arc import Arc
from comicsdb.models.attribution import Attribution

HTML_OK_CODE = 200
HTML_REDIRECT = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_arc(create_user):
    user = create_user()
    for pub_num in range(PAGINATE_TEST_VAL):
        Arc.objects.create(
            name=f"Arc {pub_num}", slug=f"arc-{pub_num}", edited_by=user, created_by=user
        )


def test_arc_detail(wwh_arc, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/arc/{wwh_arc.slug}/")
    assert resp.status_code == HTML_OK_CODE


def test_arc_redirect(wwh_arc, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/arc/{wwh_arc.pk}/")
    assert resp.status_code == HTML_REDIRECT


# Arc Search View
def test_arc_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/arc/search")
    assert resp.status_code == HTML_OK_CODE


def test_arc_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:search"))
    assert resp.status_code == HTML_OK_CODE


def test_arc_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/arc_list.html")


def test_arc_search_pagination_is_thirty(auto_login_user, list_of_arc):
    client, _ = auto_login_user()
    resp = client.get("/arc/search?q=arc")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["arc_list"]) == PAGINATE_DEFAULT_VAL


def test_arc_search_all_arcs(auto_login_user, list_of_arc):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get("/arc/search?page=2&q=arc")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["arc_list"]) == PAGINATE_DIFF_VAL


# Arc List Views
def test_arc_list_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/arc/")
    assert resp.status_code == HTML_OK_CODE


def test_arc_list_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:list"))
    assert resp.status_code == HTML_OK_CODE


def test_arc_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/arc_list.html")


def test_arc_list_pagination_is_thirty(auto_login_user, list_of_arc):
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["arc_list"]) == PAGINATE_DEFAULT_VAL


def test_arc_list_second_page(auto_login_user, list_of_arc):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["arc_list"]) == PAGINATE_DIFF_VAL


# Arc Form
def test_valid_form():
    form = ArcForm(
        data={
            "name": "Heroes in Crisis",
            "slug": "heroes-in-crisis",
            "desc": "Heroes in need of therapy",
            "image": "arc/2019/06/07/heroes-1.jpg",
        }
    )
    assert form.is_valid() is True


def test_form_invalid():
    form = ArcForm(data={"name": "", "slug": "bad-data", "desc": "", "image": ""})
    assert form.is_valid() is False


# Arc Create
def test_create_arc_view(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:create"))
    assert (
        '<input type="url" name="comicsdb-attribution-content_type-object_id-0-url" maxlength="200" '  # NOQA: E501
        'class="input is-fullwidth" id="id_comicsdb-attribution-content_type-object_id-0-url">'
        in str(resp.content)
    )
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/model_with_attribution_form.html")


def test_create_arc_validform_view(auto_login_user, wwh_arc):
    data = {
        "name": "Infinite Crisis",
        "slug": "infinite-crisis",
        "desc": "World ending crisis",
        "image": "arc/2019/06/07/crisis-1",
        "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
        "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
        "comicsdb-attribution-content_type-object_id-0-source": "W",
        "comicsdb-attribution-content_type-object_id-0-url": "https://en.wikipedia.org/wiki/Wonder_Woman",
    }
    client, _ = auto_login_user()
    arc_count = Arc.objects.count()
    resp = client.post(
        reverse("arc:create"),
        data=data,
    )
    # Should this really be HTTP 302? Probably need to see if we should be redirecting or not.
    assert resp.status_code == 302
    assert Arc.objects.count() == arc_count + 1
    assert Attribution.objects.count() == 1


# Arc Update
def test_arc_update_view(auto_login_user, wwh_arc):
    client, _ = auto_login_user()
    k = {"slug": wwh_arc.slug}
    resp = client.get(reverse("arc:update", kwargs=k))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/model_with_attribution_form.html")


# def test_arc_update_validform_view(auto_login_user, wwh_arc):
#     client, _ = auto_login_user()
#     k = {"slug": wwh_arc.slug}
#     arc_count = Arc.objects.count()
#     resp = client.post(
#         reverse("arc:update", kwargs=k),
#         {
#             "name": "War of the Realms",
#             "slug": wwh_arc.slug,
#             "desc": "Asgardian crisis",
#             "image": "",
#         },
#     )
#     # Should this really be HTTP 302? Probably need to see if we should be redirecting or
#       not.
#     assert resp.status_code == 302
#     assert Arc.objects.count() == arc_count


# Arc History Views
def test_arc_history_view_requires_login(client, wwh_arc):
    """Test that history view requires authentication."""
    resp = client.get(reverse("arc:history", kwargs={"slug": wwh_arc.slug}))
    assert resp.status_code == HTML_REDIRECT


def test_arc_history_view_url_accessible_by_name(auto_login_user, wwh_arc):
    """Test that history view is accessible by name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": wwh_arc.slug}))
    assert resp.status_code == HTML_OK_CODE


def test_arc_history_view_uses_correct_template(auto_login_user, wwh_arc):
    """Test that history view uses the correct template."""
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": wwh_arc.slug}))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/history_list.html")


def test_arc_history_shows_initial_creation(auto_login_user, create_user):
    """Test that history shows the initial creation record."""
    user = create_user()
    arc = Arc.objects.create(name="Test Arc", slug="test-arc", edited_by=user, created_by=user)
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": arc.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "history_list" in resp.context
    assert len(resp.context["history_list"]) == 1
    assert resp.context["history_list"][0].history_type == "+"


def test_arc_history_shows_updates(auto_login_user, create_user):
    """Test that history shows update records."""
    user = create_user()
    arc = Arc.objects.create(name="Test Arc", slug="test-arc", edited_by=user, created_by=user)
    # Update the arc
    arc.name = "Updated Arc"
    arc.save()

    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": arc.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert len(resp.context["history_list"]) == 2
    # History is ordered newest first
    assert resp.context["history_list"][0].history_type == "~"
    assert resp.context["history_list"][1].history_type == "+"


def test_arc_history_has_delta_information(auto_login_user, create_user):
    """Test that history records have delta information for changes."""
    user = create_user()
    arc = Arc.objects.create(
        name="Test Arc", slug="test-arc", desc="Original", edited_by=user, created_by=user
    )
    # Update the arc
    arc.desc = "Updated description"
    arc.save()

    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": arc.slug}))
    assert resp.status_code == HTML_OK_CODE
    history_list = resp.context["history_list"]
    # The most recent record should have a delta
    assert hasattr(history_list[0], "delta")
    assert history_list[0].delta is not None
    # Check that the delta contains the changed field
    changes = list(history_list[0].delta.changes)
    assert len(changes) > 0
    field_names = [change.field for change in changes]
    assert "desc" in field_names


def test_arc_history_pagination(auto_login_user, create_user):
    """Test that history view is paginated correctly."""
    user = create_user()
    arc = Arc.objects.create(name="Test Arc", slug="test-arc", edited_by=user, created_by=user)
    # Create 30 updates to trigger pagination
    for i in range(30):
        arc.desc = f"Update {i}"
        arc.save()

    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": arc.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["history_list"]) == 25


def test_arc_history_second_page(auto_login_user, create_user):
    """Test that second page of history works correctly."""
    user = create_user()
    arc = Arc.objects.create(name="Test Arc", slug="test-arc", edited_by=user, created_by=user)
    # Create 30 updates to trigger pagination
    for i in range(30):
        arc.desc = f"Update {i}"
        arc.save()

    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": arc.slug}) + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert len(resp.context["history_list"]) == 6  # 31 total - 25 on first page


def test_arc_history_handles_none_user(auto_login_user, create_user):
    """Test that history view handles records with no user (created programmatically)."""
    user = create_user()
    arc = Arc.objects.create(name="Test Arc", slug="test-arc", edited_by=user, created_by=user)

    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": arc.slug}))
    assert resp.status_code == HTML_OK_CODE
    history_record = resp.context["history_list"][0]
    # Records created directly (not through views) have no history_user
    # The template should handle this gracefully
    assert history_record.history_user is None or isinstance(
        history_record.history_user, type(user)
    )


def test_arc_history_context_has_object(auto_login_user, wwh_arc):
    """Test that history view context includes the object."""
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": wwh_arc.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "object" in resp.context
    assert resp.context["object"] == wwh_arc


def test_arc_history_context_has_model_name(auto_login_user, wwh_arc):
    """Test that history view context includes the model name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("arc:history", kwargs={"slug": wwh_arc.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "model_name" in resp.context
    assert resp.context["model_name"] == "arc"
