"""Fixtures for wiki app tests."""

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from wiki.models import Article, URLPath


@pytest.fixture
def wiki_root(db):
    """Create the root URLPath/Article for the wiki."""
    return URLPath.create_root(title="Root")


@pytest.fixture
def wiki_user(db, create_user):
    """Create a regular authenticated user for wiki tests."""
    return create_user(username="wiki_user")


@pytest.fixture
def wiki_owner(db, create_user):
    """Create a user who owns wiki articles."""
    return create_user(username="wiki_owner")


@pytest.fixture
def wiki_moderator(db, create_user):
    """Create a user with wiki.moderate permission."""
    user = create_user(username="wiki_moderator")
    ct = ContentType.objects.get_for_model(Article)
    perm = Permission.objects.get(content_type=ct, codename="moderate")
    user.user_permissions.add(perm)
    return user


@pytest.fixture
def wiki_assign_user(db, create_user):
    """Create a user with wiki.assign permission."""
    user = create_user(username="wiki_assigner")
    ct = ContentType.objects.get_for_model(Article)
    perm = Permission.objects.get(content_type=ct, codename="assign")
    user.user_permissions.add(perm)
    return user


@pytest.fixture
def wiki_child(db, wiki_root):
    """Create a child article under the root."""
    return URLPath.create_urlpath(
        wiki_root,
        "test-article",
        title="Test Article",
        content="This is test content.",
    )


@pytest.fixture
def logged_in_client(client, wiki_user, test_password):
    """Return a client logged in as wiki_user."""
    client.login(username=wiki_user.username, password=test_password)
    return client


@pytest.fixture
def owner_client(client, wiki_owner, test_password):
    """Return a client logged in as wiki_owner."""
    client.login(username=wiki_owner.username, password=test_password)
    return client
