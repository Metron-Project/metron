import pytest
from django.urls import reverse
from django.utils.text import slugify
from pytest_django.asserts import assertTemplateUsed

from comicsdb.models import Publisher
from comicsdb.models.attribution import Attribution

HTML_OK_CODE = 200
HTML_REDIRECT_CODE = 302

PAGINATE_TEST_VAL = 35
PAGINATE_DEFAULT_VAL = 28
PAGINATE_DIFF_VAL = PAGINATE_TEST_VAL - PAGINATE_DEFAULT_VAL


@pytest.fixture
def list_of_publishers(create_user):
    user = create_user()
    for pub_num in range(PAGINATE_TEST_VAL):
        Publisher.objects.create(
            name=f"Publisher {pub_num}",
            slug=f"publisher-{pub_num}",
            edited_by=user,
            created_by=user,
        )


def test_publisher_detail_requires_login(client, dc_comics):
    """Test that detail view requires authentication."""
    resp = client.get(reverse("publisher:detail", kwargs={"slug": dc_comics.slug}))
    assert resp.status_code == HTML_REDIRECT_CODE


def test_publisher_detail(dc_comics, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/publisher/{dc_comics.slug}/")
    assert resp.status_code == HTML_OK_CODE


def test_publisher_redirect(dc_comics, auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(f"/publisher/{dc_comics.pk}/")
    assert resp.status_code == HTML_REDIRECT_CODE


# def test_publisher_view_update(auto_login_user, dc_comics):
#     client, _ = auto_login_user()
#     resp = client.post(
#         reverse("publisher:update", kwargs={"slug": dc_comics.slug}),
#         {"name": "DC Comics", "slug": "dc-comics", "desc": "Test data"},
#     )
#     assert resp.status_code == 302
#     dc_comics.refresh_from_db()
#     assert dc_comics.desc == "Test data"


def test_publisher_create_view(auto_login_user, marvel):
    pub_name = "Ahoy Comics"
    pub_slug = slugify(pub_name)
    client, user = auto_login_user()
    data = {
        "name": pub_name,
        "slug": pub_slug,
        "edited_by": user,
        "country": "US",
        "comicsdb-attribution-content_type-object_id-TOTAL_FORMS": 1,
        "comicsdb-attribution-content_type-object_id-INITIAL_FORMS": 0,
        "comicsdb-attribution-content_type-object_id-0-source": "W",
        "comicsdb-attribution-content_type-object_id-0-url": "https://en.wikipedia.org/wiki/Ahoy_Comics",
    }
    publisher_count = Publisher.objects.count()
    attribution_count = Attribution.objects.count()
    resp = client.post(reverse("publisher:create"), data=data)
    assert resp.status_code == HTML_REDIRECT_CODE
    ahoy = Publisher.objects.get(slug=pub_slug)
    assert Publisher.objects.count() == publisher_count + 1
    assert Attribution.objects.count() == attribution_count + 1
    assert ahoy.name == pub_name


def test_publisher_search_view_requires_login(client):
    """Test that search view requires authentication."""
    resp = client.get(reverse("publisher:search"))
    assert resp.status_code == HTML_REDIRECT_CODE


def test_publisher_search_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/publisher/search")
    assert resp.status_code == HTML_OK_CODE


def test_publisher_search_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:search"))
    assert resp.status_code == HTML_OK_CODE


def test_publisher_search_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:search"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/publisher_list.html")


def test_publisher_search_pagination_is_thirty(auto_login_user, list_of_publishers):
    client, _ = auto_login_user()
    resp = client.get("/publisher/search?q=pub")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["publisher_list"]) == PAGINATE_DEFAULT_VAL


def test_publisher_search_lists_all_publishers(auto_login_user, list_of_publishers):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get("/publisher/search?page=2&q=pub")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["publisher_list"]) == PAGINATE_DIFF_VAL


def test_publisher_list_view_requires_login(client):
    """Test that list view requires authentication."""
    resp = client.get(reverse("publisher:list"))
    assert resp.status_code == HTML_REDIRECT_CODE


def test_publisher_list_view_url_exists_at_desired_location(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get("/publisher/")
    assert resp.status_code == HTML_OK_CODE


def test_publisher_list_view_url_accessible_by_name(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:list"))
    assert resp.status_code == HTML_OK_CODE


def test_publisher_list_view_uses_correct_template(auto_login_user):
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:list"))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/publisher_list.html")


def test_publisher_list_pagination_is_thirty(auto_login_user, list_of_publishers):
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:list"))
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["publisher_list"]) == PAGINATE_DEFAULT_VAL


def test_publisher_list_second_page(auto_login_user, list_of_publishers):
    # Get second page and confirm it has (exactly) remaining 7 items
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:list") + "?page=2")
    assert resp.status_code == HTML_OK_CODE
    assert "is_paginated" in resp.context
    assert resp.context["is_paginated"] is True
    assert len(resp.context["publisher_list"]) == PAGINATE_DIFF_VAL


# Publisher History Views
def test_publisher_history_view_requires_login(client, dc_comics):
    """Test that history view requires authentication."""
    resp = client.get(reverse("publisher:history", kwargs={"slug": dc_comics.slug}))
    assert resp.status_code == HTML_REDIRECT_CODE


def test_publisher_history_view_accessible(auto_login_user, dc_comics):
    """Test that history view is accessible by name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:history", kwargs={"slug": dc_comics.slug}))
    assert resp.status_code == HTML_OK_CODE


def test_publisher_history_uses_correct_template(auto_login_user, dc_comics):
    """Test that history view uses the correct template."""
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:history", kwargs={"slug": dc_comics.slug}))
    assert resp.status_code == HTML_OK_CODE
    assertTemplateUsed(resp, "comicsdb/history_list.html")


def test_publisher_history_shows_creation(auto_login_user, dc_comics):
    """Test that history shows the initial creation record."""
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:history", kwargs={"slug": dc_comics.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "history_list" in resp.context
    assert len(resp.context["history_list"]) >= 1


def test_publisher_history_context(auto_login_user, dc_comics):
    """Test that history view context includes object and model name."""
    client, _ = auto_login_user()
    resp = client.get(reverse("publisher:history", kwargs={"slug": dc_comics.slug}))
    assert resp.status_code == HTML_OK_CODE
    assert "object" in resp.context
    assert resp.context["object"] == dc_comics
    assert "model_name" in resp.context
    assert resp.context["model_name"] == "publisher"
