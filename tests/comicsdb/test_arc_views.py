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
