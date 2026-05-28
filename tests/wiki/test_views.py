"""Tests for wiki views: article display, create, edit, delete, history, search."""

import pytest

from wiki.models import URLPath

pytestmark = pytest.mark.django_db

HTTP_200_OK = 200
HTTP_302_FOUND = 302
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404


class TestRootView:
    """Tests for the wiki root article view."""

    def test_root_view_anonymous(self, client, wiki_root):
        """Anonymous user can view the root article (WIKI_ANONYMOUS=True by default)."""
        resp = client.get("/wiki/")
        assert resp.status_code == HTTP_200_OK

    def test_root_view_authenticated(self, logged_in_client, wiki_root):
        """Authenticated user can view the root article."""
        resp = logged_in_client.get("/wiki/")
        assert resp.status_code == HTTP_200_OK

    def test_root_view_without_root_redirects(self, client):
        """Without a root article, the wiki redirects to the create-root view."""
        resp = client.get("/wiki/")
        # Django-wiki redirects to missing-root or create-root
        assert resp.status_code == HTTP_302_FOUND


class TestArticleView:
    """Tests for viewing wiki articles by ID and by path."""

    def test_view_article_by_id_anonymous(self, client, wiki_root, wiki_child):
        """Anonymous user can view a public article by its ID."""
        resp = client.get(f"/wiki/{wiki_child.article.pk}/")
        assert resp.status_code == HTTP_200_OK

    def test_view_article_by_id_authenticated(self, logged_in_client, wiki_root, wiki_child):
        """Authenticated user can view a public article by its ID."""
        resp = logged_in_client.get(f"/wiki/{wiki_child.article.pk}/")
        assert resp.status_code == HTTP_200_OK

    def test_view_article_by_path_anonymous(self, client, wiki_root, wiki_child):
        """Anonymous user can view a public article by URL path."""
        resp = client.get(f"/wiki/{wiki_child.path}")
        assert resp.status_code == HTTP_200_OK

    def test_view_nonexistent_article_returns_404(self, client, wiki_root):
        """Requesting an article ID that does not exist returns 404."""
        resp = client.get("/wiki/99999/")
        assert resp.status_code == HTTP_404_NOT_FOUND

    def test_view_nonexistent_path_redirects_to_create(self, client, wiki_root):
        """Requesting an unknown slug path redirects to the create form."""
        resp = client.get("/wiki/does-not-exist/")
        # Django-wiki redirects to the create page for non-existent paths
        assert resp.status_code == HTTP_302_FOUND
        assert "_create" in resp["Location"]


class TestCreateView:
    """Tests for the wiki article create view."""

    def test_create_view_anonymous_redirects_to_login(self, client, wiki_root):
        """Anonymous user is redirected to login when trying to create an article."""
        resp = client.get("/wiki/_create/")
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp["Location"]

    def test_create_view_authenticated_returns_200(self, logged_in_client, wiki_root):
        """Authenticated user can access the create article form."""
        resp = logged_in_client.get("/wiki/_create/")
        assert resp.status_code == HTTP_200_OK

    def test_create_article_post(self, logged_in_client, wiki_root):
        """POST to the create view with valid data creates a new article."""
        resp = logged_in_client.post(
            "/wiki/_create/",
            {
                "title": "New Article",
                "slug": "new-article",
                "content": "This is the article content.",
                "summary": "Created in test",
            },
        )
        # Successful creation redirects to the new article
        assert resp.status_code == HTTP_302_FOUND
        assert URLPath.objects.filter(slug="new-article").exists()

    def test_create_article_duplicate_slug(self, logged_in_client, wiki_root, wiki_child):
        """Creating an article with a slug that already exists shows a form error."""
        resp = logged_in_client.post(
            "/wiki/_create/",
            {
                "title": "Duplicate",
                "slug": "test-article",  # same as wiki_child
                "content": "Duplicate content",
                "summary": "",
            },
        )
        # Form should redisplay with an error, not redirect
        assert resp.status_code == HTTP_200_OK

    def test_create_child_article(self, logged_in_client, wiki_root, wiki_child):
        """Authenticated user can create a child article under an existing article."""
        resp = logged_in_client.post(
            f"/wiki/{wiki_child.path}_create/",
            {
                "title": "Child Article",
                "slug": "child-article",
                "content": "Child content.",
                "summary": "",
            },
        )
        assert resp.status_code == HTTP_302_FOUND
        assert URLPath.objects.filter(slug="child-article").exists()


class TestEditView:
    """Tests for the wiki article edit view."""

    def test_edit_view_anonymous_redirects_to_login(self, client, wiki_root, wiki_child):
        """Anonymous user is redirected when trying to edit an article."""
        resp = client.get(f"/wiki/{wiki_child.article.pk}/edit/")
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp["Location"]

    def test_edit_view_authenticated_returns_200(self, logged_in_client, wiki_root, wiki_child):
        """Authenticated user can access the edit form."""
        resp = logged_in_client.get(f"/wiki/{wiki_child.article.pk}/edit/")
        assert resp.status_code == HTTP_200_OK

    def test_edit_article_post(self, logged_in_client, wiki_root, wiki_child):
        """POST to the edit view with valid data updates the article."""
        current_rev = wiki_child.article.current_revision
        resp = logged_in_client.post(
            f"/wiki/{wiki_child.article.pk}/edit/",
            {
                "title": "Updated Title",
                "content": "Updated content here.",
                "summary": "Fixed a typo",
                "current_revision": current_rev.pk,
                # The edit view only processes the form when save=1 is present
                "save": "1",
            },
        )
        assert resp.status_code == HTTP_302_FOUND
        wiki_child.article.refresh_from_db()
        assert wiki_child.article.current_revision.title == "Updated Title"


class TestDeleteView:
    """Tests for the wiki article delete view."""

    def test_delete_view_anonymous_redirects_to_login(self, client, wiki_root, wiki_child):
        """Anonymous user is redirected when trying to delete an article."""
        resp = client.get(f"/wiki/{wiki_child.article.pk}/delete/")
        assert resp.status_code == HTTP_302_FOUND
        assert "/accounts/login/" in resp["Location"]

    def test_delete_view_authenticated_returns_200(self, logged_in_client, wiki_root, wiki_child):
        """Authenticated user can access the delete confirmation form."""
        resp = logged_in_client.get(f"/wiki/{wiki_child.article.pk}/delete/")
        assert resp.status_code == HTTP_200_OK

    def test_delete_article_post(self, logged_in_client, wiki_root, wiki_child):
        """POST to delete marks the article as deleted."""
        article_pk = wiki_child.article.pk
        current_rev_pk = wiki_child.article.current_revision.pk
        resp = logged_in_client.post(
            f"/wiki/{article_pk}/delete/",
            {
                "confirm": "on",
                "revision": current_rev_pk,
            },
        )
        assert resp.status_code == HTTP_302_FOUND
        wiki_child.article.refresh_from_db()
        assert wiki_child.article.current_revision.deleted is True


class TestHistoryView:
    """Tests for the wiki article history view."""

    def test_history_view_anonymous(self, client, wiki_root, wiki_child):
        """Anonymous user can view the revision history."""
        resp = client.get(f"/wiki/{wiki_child.article.pk}/history/")
        assert resp.status_code == HTTP_200_OK

    def test_history_view_authenticated(self, logged_in_client, wiki_root, wiki_child):
        """Authenticated user can view the revision history."""
        resp = logged_in_client.get(f"/wiki/{wiki_child.article.pk}/history/")
        assert resp.status_code == HTTP_200_OK


class TestSourceView:
    """Tests for the wiki article source view."""

    def test_source_view_anonymous(self, client, wiki_root, wiki_child):
        """Anonymous user can view the raw markdown source."""
        resp = client.get(f"/wiki/{wiki_child.article.pk}/source/")
        assert resp.status_code == HTTP_200_OK

    def test_source_view_authenticated(self, logged_in_client, wiki_root, wiki_child):
        """Authenticated user can view the raw markdown source."""
        resp = logged_in_client.get(f"/wiki/{wiki_child.article.pk}/source/")
        assert resp.status_code == HTTP_200_OK


class TestSettingsView:
    """Tests for the wiki article settings view."""

    def test_settings_view_anonymous_redirects(self, client, wiki_root, wiki_child):
        """Anonymous user is redirected from the settings view."""
        resp = client.get(f"/wiki/{wiki_child.article.pk}/settings/")
        assert resp.status_code == HTTP_302_FOUND

    def test_settings_view_authenticated(self, logged_in_client, wiki_root, wiki_child):
        """Authenticated user can access the article settings."""
        resp = logged_in_client.get(f"/wiki/{wiki_child.article.pk}/settings/")
        assert resp.status_code == HTTP_200_OK


class TestSearchView:
    """Tests for the wiki search view."""

    def test_search_anonymous(self, client, wiki_root):
        """Anonymous user can use the search view."""
        resp = client.get("/wiki/_search/", {"q": "test"})
        assert resp.status_code == HTTP_200_OK

    def test_search_authenticated(self, logged_in_client, wiki_root):
        """Authenticated user can search the wiki."""
        resp = logged_in_client.get("/wiki/_search/", {"q": "article"})
        assert resp.status_code == HTTP_200_OK

    def test_search_empty_query(self, client, wiki_root):
        """Search with no query term returns the search page."""
        resp = client.get("/wiki/_search/")
        assert resp.status_code == HTTP_200_OK

    def test_search_finds_article(self, client, wiki_root, wiki_child):
        """Searching for content that exists returns results."""
        resp = client.get("/wiki/_search/", {"q": "Test Article"})
        assert resp.status_code == HTTP_200_OK
