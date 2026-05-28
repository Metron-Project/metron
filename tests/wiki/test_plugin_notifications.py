"""Tests for the wiki notifications plugin."""

import pytest

from wiki.models import ArticleRevision, URLPath

pytestmark = pytest.mark.django_db


class TestNotificationSignal:
    """Tests for the post_article_revision_save signal handler."""

    def test_creating_revision_does_not_raise(self, wiki_root):
        """Creating a new ArticleRevision fires the notifications signal without error.

        The signal calls django_nyt.utils.notify() for new revisions. This test
        verifies the signal handler runs cleanly even when no subscribers exist.
        """
        rev = ArticleRevision(title="Signal Test", content="Some content.")
        # add_revision triggers post_save → post_article_revision_save
        wiki_root.article.add_revision(rev, save=True)
        # No exception means the signal handler ran without error
        assert rev.pk is not None

    def test_editing_revision_does_not_raise(self, wiki_root):
        """Updating an article (adding a second revision) fires the signal cleanly."""
        rev1 = ArticleRevision(title="First", content="v1")
        wiki_root.article.add_revision(rev1, save=True)

        rev2 = ArticleRevision(title="Second", content="v2")
        wiki_root.article.add_revision(rev2, save=True)

        assert rev2.previous_revision == rev1

    def test_deleted_revision_does_not_raise(self, wiki_child):
        """Marking a revision deleted fires the signal without error."""
        rev = ArticleRevision(
            title=wiki_child.article.current_revision.title,
            content="",
            deleted=True,
        )
        wiki_child.article.add_revision(rev, save=True)
        assert rev.pk is not None
        assert rev.deleted is True

    def test_new_child_article_signal(self, wiki_root):
        """Creating a brand-new child article via URLPath fires the signal cleanly."""
        child = URLPath.create_urlpath(
            wiki_root,
            "notification-test",
            title="Notification Test",
            content="Test body.",
        )
        assert child.pk is not None
        assert child.article.current_revision.title == "Notification Test"
