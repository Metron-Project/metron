"""Tests for wiki permission logic (wiki/core/permissions.py)."""

import pytest
from django.contrib.auth.models import AnonymousUser

from wiki.core import permissions
from wiki.models import Article, ArticleRevision

pytestmark = pytest.mark.django_db


@pytest.fixture
def open_article(db):
    """Article with other_read=True, other_write=True (world-readable)."""
    article = Article(other_read=True, other_write=True)
    revision = ArticleRevision(title="Open", content="open")
    article.add_revision(revision, save=True)
    return article


@pytest.fixture
def restricted_article(db):
    """Article with other_read=False, other_write=False, group_read=False, group_write=False."""
    article = Article(
        other_read=False,
        other_write=False,
        group_read=False,
        group_write=False,
    )
    revision = ArticleRevision(title="Restricted", content="private")
    article.add_revision(revision, save=True)
    return article


@pytest.fixture
def owner_article(db, wiki_owner):
    """Article owned by wiki_owner, no other/group access."""
    article = Article(
        owner=wiki_owner,
        other_read=False,
        other_write=False,
        group_read=False,
        group_write=False,
    )
    revision = ArticleRevision(title="Owned", content="mine")
    article.add_revision(revision, save=True)
    return article


@pytest.fixture
def deleted_article(db):
    """Article whose current revision is marked deleted."""
    article = Article(other_read=True, other_write=True)
    revision = ArticleRevision(title="Deleted", content="gone", deleted=True)
    article.add_revision(revision, save=True)
    return article


class TestCanRead:
    """Tests for permissions.can_read()."""

    def test_anonymous_can_read_when_other_read(self, open_article):
        """Anonymous user can read an article with other_read=True."""
        user = AnonymousUser()
        assert permissions.can_read(open_article, user) is True

    def test_authenticated_can_read_when_other_read(self, open_article, wiki_user):
        """Authenticated user can read an article with other_read=True."""
        assert permissions.can_read(open_article, wiki_user) is True

    def test_anonymous_cannot_read_restricted(self, restricted_article):
        """Anonymous user cannot read an article with other_read=False."""
        user = AnonymousUser()
        assert permissions.can_read(restricted_article, user) is False

    def test_owner_can_always_read(self, owner_article, wiki_owner):
        """Article owner can read even when other_read=False."""
        assert permissions.can_read(owner_article, wiki_owner) is True

    def test_non_owner_cannot_read_restricted(self, restricted_article, wiki_user):
        """Non-owner cannot read when other_read and group_read are False."""
        assert permissions.can_read(restricted_article, wiki_user) is False

    def test_moderator_can_read_restricted(self, restricted_article, wiki_moderator):
        """A moderator can read any article regardless of permissions."""
        assert permissions.can_read(restricted_article, wiki_moderator) is True

    def test_anonymous_cannot_read_deleted_article(self, deleted_article):
        """Anonymous users cannot read a deleted article."""
        user = AnonymousUser()
        assert permissions.can_read(deleted_article, user) is False

    def test_moderator_can_read_deleted_article(self, deleted_article, wiki_moderator):
        """Moderators can read deleted articles (they have can_delete access)."""
        assert permissions.can_read(deleted_article, wiki_moderator) is True


class TestCanWrite:
    """Tests for permissions.can_write()."""

    def test_anonymous_cannot_write_by_default(self, open_article):
        """Anonymous users cannot write even when other_write=True (ANONYMOUS_WRITE=False)."""
        user = AnonymousUser()
        # WIKI_ANONYMOUS_WRITE defaults to False in this project
        assert permissions.can_write(open_article, user) is False

    def test_authenticated_can_write_when_other_write(self, open_article, wiki_user):
        """Authenticated user can write when other_write=True."""
        assert permissions.can_write(open_article, wiki_user) is True

    def test_owner_can_always_write(self, owner_article, wiki_owner):
        """Article owner can write even when other_write=False."""
        assert permissions.can_write(owner_article, wiki_owner) is True

    def test_non_owner_cannot_write_restricted(self, restricted_article, wiki_user):
        """Non-owner cannot write when other_write and group_write are False."""
        assert permissions.can_write(restricted_article, wiki_user) is False

    def test_moderator_can_write_restricted(self, restricted_article, wiki_moderator):
        """A moderator can write any article."""
        assert permissions.can_write(restricted_article, wiki_moderator) is True


class TestCanDelete:
    """Tests for permissions.can_delete()."""

    def test_anonymous_cannot_delete(self, open_article):
        """Anonymous users cannot delete articles."""
        user = AnonymousUser()
        assert permissions.can_delete(open_article, user) is False

    def test_writer_can_delete(self, open_article, wiki_user):
        """A user who can write can also delete."""
        assert permissions.can_delete(open_article, wiki_user) is True

    def test_non_writer_cannot_delete(self, restricted_article, wiki_user):
        """A user who cannot write cannot delete."""
        assert permissions.can_delete(restricted_article, wiki_user) is False


class TestCanModerate:
    """Tests for permissions.can_moderate()."""

    def test_anonymous_cannot_moderate(self, open_article):
        """Anonymous users cannot moderate."""
        user = AnonymousUser()
        assert permissions.can_moderate(open_article, user) is False

    def test_regular_user_cannot_moderate(self, open_article, wiki_user):
        """Regular users without the wiki.moderate permission cannot moderate."""
        assert permissions.can_moderate(open_article, wiki_user) is False

    def test_moderator_can_moderate(self, open_article, wiki_moderator):
        """Users with wiki.moderate permission can moderate."""
        assert permissions.can_moderate(open_article, wiki_moderator) is True


class TestCanAssign:
    """Tests for permissions.can_assign()."""

    def test_anonymous_cannot_assign(self, open_article):
        """Anonymous users cannot assign permissions."""
        user = AnonymousUser()
        assert permissions.can_assign(open_article, user) is False

    def test_regular_user_cannot_assign(self, open_article, wiki_user):
        """Regular users without wiki.assign cannot assign."""
        assert permissions.can_assign(open_article, wiki_user) is False

    def test_assign_user_can_assign(self, open_article, wiki_assign_user):
        """Users with wiki.assign permission can assign."""
        assert permissions.can_assign(open_article, wiki_assign_user) is True


class TestCanChangePermissions:
    """Tests for permissions.can_change_permissions()."""

    def test_anonymous_cannot_change_permissions(self, owner_article):
        """Anonymous users cannot change article permissions."""
        user = AnonymousUser()
        assert permissions.can_change_permissions(owner_article, user) is False

    def test_owner_can_change_permissions(self, owner_article, wiki_owner):
        """The article owner can change permissions."""
        assert permissions.can_change_permissions(owner_article, wiki_owner) is True

    def test_non_owner_cannot_change_permissions(self, owner_article, wiki_user):
        """Non-owners without wiki.assign cannot change permissions."""
        assert permissions.can_change_permissions(owner_article, wiki_user) is False

    def test_assign_user_can_change_permissions(self, owner_article, wiki_assign_user):
        """Users with wiki.assign can change permissions."""
        assert permissions.can_change_permissions(owner_article, wiki_assign_user) is True
