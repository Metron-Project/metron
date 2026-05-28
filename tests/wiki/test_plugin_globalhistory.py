"""Tests for the wiki globalhistory plugin view.

Note: wiki.plugins.globalhistory is not in INSTALLED_APPS, so its URL is not
mounted and its templates are not on the search path. Tests call the view
directly via RequestFactory and inspect context_data without rendering.
"""

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from wiki.models import ArticleRevision
from wiki.plugins.globalhistory.views import GlobalHistory

pytestmark = pytest.mark.django_db


@pytest.fixture
def rf():
    return RequestFactory()


class TestGlobalHistoryView:
    """Tests for the GlobalHistory plugin view."""

    def test_anonymous_redirects_to_login(self, rf, wiki_root):
        """Anonymous users are redirected to login (view is login_required)."""
        request = rf.get("/")
        request.user = AnonymousUser()
        response = GlobalHistory.as_view()(request)
        assert response.status_code == 302
        assert "/accounts/login/" in response["Location"]

    def test_authenticated_returns_200(self, rf, wiki_root, wiki_user):
        """Authenticated users get a 200 response (before template rendering)."""
        request = rf.get("/")
        request.user = wiki_user
        response = GlobalHistory.as_view()(request)
        assert response.status_code == 200

    def test_shows_revisions_in_context(self, rf, wiki_root, wiki_child, wiki_user):
        """The response context contains revisions for all readable articles."""
        request = rf.get("/")
        request.user = wiki_user
        response = GlobalHistory.as_view()(request)
        revisions = response.context_data["revisions"]
        # Root and child articles each have at least one revision
        assert revisions.count() >= 2

    def test_only_last_filter_reduces_count(self, rf, wiki_root, wiki_child, wiki_user):
        """Passing only_last='1' returns fewer or equal revisions than no filter."""
        # Add a second revision to the child
        rev = ArticleRevision(title="Updated", content="Updated content.")
        wiki_child.article.add_revision(rev, save=True)

        request_all = rf.get("/")
        request_all.user = wiki_user
        count_all = GlobalHistory.as_view()(request_all).context_data["revisions"].count()

        request_last = rf.get("/")
        request_last.user = wiki_user
        count_last = (
            GlobalHistory.as_view()(request_last, only_last="1")
            .context_data["revisions"]
            .count()
        )

        assert count_last <= count_all

    def test_revisions_ordered_newest_first(self, rf, wiki_root, wiki_child, wiki_user):
        """Revisions are returned newest-first in the queryset."""
        request = rf.get("/")
        request.user = wiki_user
        revisions = list(
            GlobalHistory.as_view()(request).context_data["revisions"]
        )
        dates = [r.modified for r in revisions]
        assert dates == sorted(dates, reverse=True)
