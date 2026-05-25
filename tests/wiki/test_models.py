"""Tests for wiki models: Article, ArticleRevision, URLPath."""

import pytest
from django.contrib.sites.models import Site

from wiki.core.exceptions import NoRootURL
from wiki.models import Article, ArticleRevision, URLPath

pytestmark = pytest.mark.django_db


class TestArticle:
    """Tests for the Article model."""

    def test_create_article_with_revision(self):
        """An article can be created and linked to a revision."""
        article = Article()
        revision = ArticleRevision(title="My Article", content="Hello, wiki!")
        article.add_revision(revision, save=True)

        assert article.pk is not None
        assert article.current_revision == revision
        assert article.current_revision.title == "My Article"

    def test_add_revision_increments_number(self):
        """Adding multiple revisions increments the revision number."""
        article = Article()
        rev1 = ArticleRevision(title="First", content="v1")
        article.add_revision(rev1, save=True)

        rev2 = ArticleRevision(title="Second", content="v2")
        article.add_revision(rev2, save=True)

        # The pre_save signal sets revision_number to 1 for the first revision,
        # then increments for each subsequent one.
        assert rev2.revision_number > rev1.revision_number
        assert article.current_revision == rev2
        assert rev2.previous_revision == rev1

    def test_add_revision_links_previous(self):
        """Each new revision stores a reference to the previous one."""
        article = Article()
        rev1 = ArticleRevision(title="Initial", content="start")
        article.add_revision(rev1, save=True)

        rev2 = ArticleRevision(title="Updated", content="updated")
        article.add_revision(rev2, save=True)

        assert rev2.previous_revision == rev1

    def test_article_revision_set(self):
        """All revisions are accessible via the reverse relation."""
        article = Article()
        rev1 = ArticleRevision(title="Rev 1", content="v1")
        article.add_revision(rev1, save=True)
        rev2 = ArticleRevision(title="Rev 2", content="v2")
        article.add_revision(rev2, save=True)

        assert article.articlerevision_set.count() == 2

    def test_can_read_defaults(self):
        """A fresh article with default permissions allows other_read."""
        article = Article()
        revision = ArticleRevision(title="Open Article", content="")
        article.add_revision(revision, save=True)

        assert article.other_read is True
        assert article.other_write is True

    def test_render_markdown(self):
        """Article.render() converts markdown content to HTML."""
        article = Article()
        revision = ArticleRevision(title="Render Test", content="**bold**")
        article.add_revision(revision, save=True)

        rendered = article.render()
        assert "<strong>bold</strong>" in rendered

    def test_get_cached_content(self):
        """get_cached_content() returns rendered HTML and caches it."""
        article = Article()
        revision = ArticleRevision(title="Cache Test", content="*italic*")
        article.add_revision(revision, save=True)

        content = article.get_cached_content()
        assert "<em>italic</em>" in content

        # Second call should return cached version
        content2 = article.get_cached_content()
        assert content == content2

    def test_clear_cache(self):
        """clear_cache() removes the cached rendered content."""
        article = Article()
        revision = ArticleRevision(title="Cache Clear", content="text")
        article.add_revision(revision, save=True)

        # Populate cache
        article.get_cached_content()
        # Clear it — should not raise
        article.clear_cache()


class TestURLPath:
    """Tests for the URLPath model and wiki hierarchy."""

    def test_create_root(self):
        """create_root() creates a root URLPath with an article."""
        root = URLPath.create_root(title="Root")

        assert root.pk is not None
        assert root.parent is None
        assert root.slug is None
        assert root.article is not None
        assert root.article.current_revision.title == "Root"

    def test_create_root_idempotent(self):
        """Calling create_root() twice returns the existing root."""
        root1 = URLPath.create_root(title="Root")
        root2 = URLPath.create_root(title="Root")

        assert root1.pk == root2.pk

    def test_root_path_is_empty_string(self):
        """The root URLPath has an empty path."""
        root = URLPath.create_root(title="Root")
        assert root.path == ""

    def test_create_child_urlpath(self):
        """create_urlpath() creates a child article with a slug."""
        root = URLPath.create_root(title="Root")
        child = URLPath.create_urlpath(
            root,
            "my-article",
            title="My Article",
            content="Some content.",
        )

        assert child.pk is not None
        assert child.parent == root
        assert child.slug == "my-article"
        assert child.article.current_revision.title == "My Article"

    def test_child_path(self):
        """A child article's path is its slug followed by a slash."""
        root = URLPath.create_root(title="Root")
        child = URLPath.create_urlpath(root, "comics", title="Comics")

        assert child.path == "comics/"

    def test_nested_child_path(self):
        """A grandchild's path includes all ancestor slugs."""
        root = URLPath.create_root(title="Root")
        child = URLPath.create_urlpath(root, "publishers", title="Publishers")
        grandchild = URLPath.create_urlpath(
            child, "dc", title="DC Comics"
        )

        assert grandchild.path == "publishers/dc/"

    def test_get_by_path_root(self):
        """get_by_path('') returns the root URLPath."""
        root = URLPath.create_root(title="Root")
        found = URLPath.get_by_path("")

        assert found.pk == root.pk

    def test_get_by_path_child(self):
        """get_by_path finds a child article by slug."""
        root = URLPath.create_root(title="Root")
        child = URLPath.create_urlpath(root, "heroes", title="Heroes")

        found = URLPath.get_by_path("heroes")
        assert found.pk == child.pk

    def test_get_by_path_nested(self):
        """get_by_path resolves multi-level paths."""
        root = URLPath.create_root(title="Root")
        parent = URLPath.create_urlpath(root, "parent", title="Parent")
        child = URLPath.create_urlpath(parent, "child", title="Child")

        found = URLPath.get_by_path("parent/child")
        assert found.pk == child.pk

    def test_get_by_path_case_insensitive(self):
        """get_by_path is case-insensitive by default."""
        root = URLPath.create_root(title="Root")
        URLPath.create_urlpath(root, "heroes", title="Heroes")

        found = URLPath.get_by_path("HEROES")
        assert found.slug == "heroes"

    def test_root_raises_without_root(self):
        """URLPath.root() raises NoRootURL when no root exists."""


        with pytest.raises(NoRootURL):
            URLPath.root()

    def test_site_association(self):
        """A URLPath is associated with the current Django site."""
        root = URLPath.create_root(title="Root")
        current_site = Site.objects.get_current()

        assert root.site == current_site

    def test_urlpath_str_root(self):
        """str() on the root returns '(root)'."""
        root = URLPath.create_root(title="Root")
        assert "(root)" in str(root)

    def test_urlpath_str_child(self):
        """str() on a child returns its path."""
        root = URLPath.create_root(title="Root")
        child = URLPath.create_urlpath(root, "test", title="Test")

        assert "test/" in str(child)

    def test_is_deleted_false_by_default(self):
        """is_deleted() returns False for a live article."""
        root = URLPath.create_root(title="Root")
        child = URLPath.create_urlpath(root, "live", title="Live")

        assert child.is_deleted() is False
