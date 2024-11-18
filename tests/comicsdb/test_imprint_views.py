import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from comicsdb.models import Imprint

HTML_OK_CODE = 200
HTML_REDIRECT_CODE = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_imprints(create_user, dc_comics):
    user = create_user()
    for imprint_num in range(PAGINATE_TEST_VAL):
        Imprint.objects.create(
            name=f"Imprint {imprint_num}",
            slug=f"imprint-{imprint_num}",
            publisher=dc_comics,
            edited_by=user,
            created_by=user,
        )


# def test_imprint_create_view(auto_login_user, dc_comics, imprint):
#     imprint_name = "Atlas"
#     imprint_slug = slugify(imprint_name)
#     client, user = auto_login_user()
#     data = {
#         "name": imprint_name,
#         "slug": imprint_slug,
#         "imprint": dc_comics.id,
#         "edited_by": user,
#         "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
#         "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
#         "comicsdb-attribution-content_type-object_id-0-source": "W",
#         "comicsdb-attribution-content_type-object_id-0-url": "https://en.wikipedia.org/wiki/Atlas_Comics",
#     }
#     imprint_count = Imprint.objects.count()
#     attribution_count = Attribution.objects.count()
#     print(f"Imprint Count: {imprint_count}\nAttribution Count: {attribution_count}")
#     resp = client.post(reverse("imprint:create"), data=data)
#     print(resp.context)
#     assert resp.status_code == HTML_REDIRECT_CODE
#     atlas = Imprint.objects.get(slug=imprint_slug)
#     assert Imprint.objects.count() == imprint_count + 1
#     assert Attribution.objects.count() == attribution_count + 1
#     assert atlas.name == imprint_name


def test_imprint_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/imprint/search")
    assert resp.status_code == HTML_OK_CODE


def test_imprint_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("imprint:search"))
    assert resp.status_code == HTML_OK_CODE


def test_imprint_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("imprint:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/imprint_list.html")


def test_imprint_search_pagination_is_thirty(auto_login_user, list_of_imprints):
    client, _ = auto_login_user()
    resp = client.get("/imprint/search?q=imprint")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["imprint_list"]) == PAGINATE_DEFAULT_VAL


def test_imprint_search_lists_all_imprints(auto_login_user, list_of_imprints):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get("/imprint/search?page=2&q=imprint")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["imprint_list"]) == PAGINATE_DIFF_VAL


def test_imprint_list_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/imprint/")
    assert resp.status_code == HTML_OK_CODE


def test_imprint_list_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("imprint:list"))
    assert resp.status_code == HTML_OK_CODE


def test_imprint_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("imprint:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/imprint_list.html")


def test_imprint_list_pagination_is_thirty(auto_login_user, list_of_imprints):
    client, _ = auto_login_user()
    resp = client.get(reverse("imprint:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["imprint_list"]) == PAGINATE_DEFAULT_VAL


def test_imprint_list_second_page(auto_login_user, list_of_imprints):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("imprint:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["imprint_list"]) == PAGINATE_DIFF_VAL
