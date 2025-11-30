import pytest
from django.urls import reverse
from pytest_django.asserts import assertTemplateUsed

from comicsdb.forms.character import CharacterForm
from comicsdb.models.attribution import Attribution
from comicsdb.models.character import Character

HTML_OK_CODE = 200
HTML_REDIRECT = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_characters(create_user):
    user = create_user()
    for pub_num in range(PAGINATE_TEST_VAL):
        Character.objects.create(
            name=f"Character {pub_num}",
            slug=f"character-{pub_num}",
            edited_by=user,
            created_by=user,
        )


def test_character_detail_requires_login(client, superman):
    """Test that detail view requires authentication."""
    resp = client.get(reverse("character:detail", kwargs={"slug": superman.slug}))
    assert resp.status_code == HTML_REDIRECT


def test_character_detail(superman, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/character/superman/")
    assert resp.status_code == HTML_OK_CODE


def test_character_redirect(superman, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/character/{superman.id}/")
    assert resp.status_code == HTML_REDIRECT


# Character Search
def test_character_search_view_requires_login(client):
    """Test that search view requires authentication."""
    resp = client.get(reverse("character:search"))
    assert resp.status_code == HTML_REDIRECT


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
def test_character_list_view_requires_login(client):
    """Test that list view requires authentication."""
    resp = client.get(reverse("character:list"))
    assert resp.status_code == HTML_REDIRECT


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


def test_create_character_validform_view(auto_login_user, batman):
    c_name = "Hulk"
    c_slug = "hulk"
    c_desc = "Gamma powered goliath."
    c_alias = ["Green Goliath"]
    data = {
        "name": c_name,
        "slug": c_slug,
        "desc": c_desc,
        "alias": c_alias,
        "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
        "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
        "comicsdb-attribution-content_type-object_id-0-source": "W",
        "comicsdb-attribution-content_type-object_id-0-url": "https://en.wikipedia.org/wiki/Hulk",
    }
    character_count = Character.objects.count()
    client, _ = auto_login_user()
    response = client.post(reverse("character:create"), data=data)
    assert response.status_code == 302
    assert Character.objects.count() == character_count + 1
    assert Attribution.objects.count() == 1
    h = Character.objects.get(slug=c_slug)
    assert h.name == c_name
    assert h.desc == c_desc
    assert h.alias == c_alias


# Character Update
def test_character_update_view(auto_login_user, batman):
    client, _ = auto_login_user()
    k = {"slug": batman.slug}
    response = client.get(reverse("character:update", kwargs=k))
    assert response.status_code == HTML_OK_CODE
    assertTemplateUsed(response, "comicsdb/model_with_attribution_form.html")


# TODO: Need to rewrite this test to handle the inline formset
#
# def test_character_update_validform_view(auto_login_user, batman):
#     client, _ = auto_login_user()
#     k = {"slug": batman.slug}
#     character_count = Character.objects.count()
#     response = client.post(
#         reverse("character:update", kwargs=k),
#         {
#             "name": "Batman",
#             "slug": batman.slug,
#             "desc": "The Dark Knight.",
#             "image": "character/2019/06/07/batman.jpg",
#         },
#     )
#     assert response.status_code == 302
#     assert Character.objects.count() == character_count


# Character History Views
def test_character_history_view_requires_login(client, superman):
    """Test that history view requires authentication."""
    resp = client.get(reverse("character:history", kwargs={"slug": superman.slug}))
    assert resp.status_code == HTML_REDIRECT


def test_character_history_view_accessible(auto_login_user, superman):
    """Test that history view is accessible by name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("character:history", kwargs={"slug": superman.slug}))
    assert resp.status_code == HTML_OK_CODE


def test_character_history_uses_correct_template(auto_login_user, superman):
    """Test that history view uses the correct template."""
    client, _ = auto_login_user()
    resp = client.get(reverse("character:history", kwargs={"slug": superman.slug}))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/history_list.html")


def test_character_history_shows_creation(auto_login_user, superman):
    """Test that history shows the initial creation record."""
    client, _ = auto_login_user()
    resp = client.get(reverse("character:history", kwargs={"slug": superman.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "history_list" in resp.context
    assert len(resp.context["history_list"]) >= 1


def test_character_history_context(auto_login_user, superman):
    """Test that history view context includes object and model name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("character:history", kwargs={"slug": superman.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "object" in resp.context
    assert resp.context["object"] == superman
    assert "model_name" in resp.context
    assert resp.context["model_name"] == "character"


def test_character_history_m2m_shows_names(
    auto_login_user, create_user, john_byrne, walter_simonson
):
    """Test that M2M field changes show object names instead of IDs."""
    user = create_user()
    character = Character.objects.create(
        name="Test Hero",
        slug="test-hero",
        created_by=user,
        edited_by=user,
    )

    # Add a creator to trigger M2M history
    character.creators.add(john_byrne)

    # Add another creator
    character.creators.add(walter_simonson)

    client, _ = auto_login_user()
    resp = client.get(reverse("character:history", kwargs={"slug": character.slug}))
    assert resp.status_code == HTML_OK_CODE

    # Check that the history list has delta information
    history_list = resp.context["history_list"]
    assert len(history_list) >= 2

    # Find a record with delta changes for creators
    found_creator_change = False
    for history_record in history_list:
        if history_record.delta:
            for change in history_record.delta.changes:
                if change.field == "creators":
                    found_creator_change = True
                    # Verify that the change shows names, not just IDs
                    # The values should contain the creator names
                    if change.new:
                        assert "John Byrne" in str(change.new) or "Walter Simonson" in str(
                            change.new
                        )
                    break
        if found_creator_change:
            break

    assert found_creator_change, "Should have found at least one creator change in history"
