import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from comicsdb.forms.character import CharacterForm
from comicsdb.models import Character

HTML_OK_CODE = 200

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_characters(create_user):
    user = create_user()
    for pub_num in range(PAGINATE_TEST_VAL):
        Character.objects.create(
            name="Character %s" % pub_num,
            slug="character-%s" % pub_num,
            edited_by=user,
        )


# Character Search
def test_character_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/character/search")
    assert resp.status_code == HTML_OK_CODE


def test_character_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("character:search"))
    assert resp.status_code == HTML_OK_CODE


def test_character_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("character:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/character_list.html")


def test_character_search_pagination_is_thirty(auto_login_user, list_of_characters):
    client, _ = auto_login_user()
    resp = client.get("/character/search?q=char")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["character_list"]) == PAGINATE_DEFAULT_VAL


def test_character_search_lists_all_characters(auto_login_user, list_of_characters):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get("/character/search?page=2&q=char")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["character_list"]) == PAGINATE_DIFF_VAL


# Character List
def test_character_list_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/character/")
    assert resp.status_code == HTML_OK_CODE


def test_character_list_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("character:list"))
    assert resp.status_code == HTML_OK_CODE


def test_character_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("character:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/character_list.html")


def test_character_list_pagination_is_thirty(auto_login_user, list_of_characters):
    client, _ = auto_login_user()
    resp = client.get(reverse("character:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["character_list"]) == PAGINATE_DEFAULT_VAL


def test_character_list_lists_second_page(auto_login_user, list_of_characters):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("character:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["character_list"]) == PAGINATE_DIFF_VAL


# Character Form
def test_valid_form():
    form = CharacterForm(
        data={
            "name": "Batman",
            "slug": "batman",
            "desc": "The Dark Knight.",
            "image": "character/2019/06/07/batman.jpg",
            "alias": "Dark Knight",
            "creators": "",
            "teams": "",
        }
    )
    assert form.is_valid() is True


def test_form_invalid():
    form = CharacterForm(
        data={
            "name": "",
            "slug": "bad-data",
            "desc": "",
            "image": "",
            "alias": "",
            "creators": "",
            "teams": "",
        }
    )
    assert form.is_valid() is False


# Character Create
def test_create_character_view(auto_login_user):
    client, _ = auto_login_user()
    response = client.get(reverse("character:create"))
    assert response.status_code == HTML_OK_CODE
    assertTemplateUsed(response, "comicsdb/model_with_attribution_form.html")


# TODO: Need to rewrite this test to handle the inline formset
#
# def test_create_character_validform_view(auto_login_user, batman):
#     character_count = Character.objects.count()
#     client, _ = auto_login_user()
#     response = client.post(
#         reverse("character:create"),
#         {
#             "name": "Hulk",
#             "slug": "hulk",
#             "desc": "Gamma powered goliath.",
#             "image": "character/2019/06/07/hulk.jpg",
#             "alias": "Green Goliath",
#         },
#     )
#     assert response.status_code == 302
#     assert Character.objects.count() == character_count + 1


# Character Update
def test_character_update_view(auto_login_user, batman):
    client, _ = auto_login_user()
    k = {"slug": batman.slug}
    response = client.get(reverse("character:update", kwargs=k))
    assert response.status_code == HTML_OK_CODE
    assertTemplateUsed(response, "comicsdb/model_with_image_form.html")


def test_character_update_validform_view(auto_login_user, batman):
    client, _ = auto_login_user()
    k = {"slug": batman.slug}
    character_count = Character.objects.count()
    response = client.post(
        reverse("character:update", kwargs=k),
        {
            "name": "Batman",
            "slug": batman.slug,
            "desc": "The Dark Knight.",
            "image": "character/2019/06/07/batman.jpg",
        },
    )
    assert response.status_code == 302
    assert Character.objects.count() == character_count
