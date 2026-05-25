"""Tests for the wiki links plugin.

Note: wiki.plugins.links is not in INSTALLED_APPS, so its URL is not mounted
under the wiki routing. Tests call the view directly via RequestFactory to
bypass URL dispatch while still exercising the view logic.
"""

import json

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from wiki.plugins.links.views import QueryUrlPath

pytestmark = pytest.mark.django_db


@pytest.fixture
def rf():
    return RequestFactory()


class TestQueryUrlPathView:
    """Tests for the links plugin JSON autocomplete endpoint."""

    def _call_view(self, rf, article_id, query=None, user=None):
        """Call the QueryUrlPath view directly, bypassing URL routing."""
        params = {"query": query} if query else {}
        request = rf.get("/", params)
        request.user = user or AnonymousUser()
        return QueryUrlPath.as_view()(request, article_id=article_id)

    def test_returns_json_response(self, rf, wiki_root):
        """The endpoint returns a JSON array."""
        resp = self._call_view(rf, wiki_root.article.pk, query="Root")
        assert resp.status_code == 200
        assert "application/json" in resp["Content-Type"]

    def test_empty_query_returns_empty_list(self, rf, wiki_root):
        """A request with no query parameter returns an empty JSON array."""
        resp = self._call_view(rf, wiki_root.article.pk)
        data = json.loads(resp.content)
        assert data == []

    def test_query_matches_article_title(self, rf, wiki_root, wiki_child):
        """A matching query returns markdown link entries for found articles."""
        resp = self._call_view(rf, wiki_root.article.pk, query="Test Article")
        data = json.loads(resp.content)
        assert len(data) >= 1
        assert any("Test Article" in entry for entry in data)

    def test_results_use_wiki_link_format(self, rf, wiki_root, wiki_child):
        """Each result entry is formatted as a markdown wiki link."""
        resp = self._call_view(rf, wiki_root.article.pk, query="Test")
        data = json.loads(resp.content)
        for entry in data:
            # Format: [Title](wiki:/path)
            assert "wiki:" in entry

    def test_query_no_match_returns_empty(self, rf, wiki_root):
        """A query with no matching articles returns an empty list."""
        resp = self._call_view(
            rf, wiki_root.article.pk, query="zzz-no-such-article-xyz"
        )
        data = json.loads(resp.content)
        assert data == []
