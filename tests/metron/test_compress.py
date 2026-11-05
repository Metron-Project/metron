"""Smoke tests for the django-compressor integration.

Compression is disabled under DEBUG (development and tests), so these tests switch it on
with online compression and send the generated bundles to a temporary directory.
Note that compressor caches rendered tag output in the default (Redis) cache, so a run may
reuse output from a previous run instead of writing new bundles.
"""

import re

import pytest
from django.urls import reverse

HTML_OK_CODE = 200


@pytest.fixture
def compress_enabled(settings, tmp_path):
    settings.COMPRESS_ENABLED = True
    settings.COMPRESS_OFFLINE = False
    settings.STORAGES = {
        **settings.STORAGES,
        "compressor": {
            "BACKEND": "compressor.storage.CompressorFileStorage",
            "OPTIONS": {"location": str(tmp_path), "base_url": "/static/"},
        },
    }
    return tmp_path


def test_base_template_assets_are_bundled(db, client, compress_enabled):
    resp = client.get(reverse("home"))
    assert resp.status_code == HTML_OK_CODE
    content = resp.content.decode()

    # The individual site stylesheets/scripts are replaced by hashed bundles.
    assert "site/css/base.css" not in content
    assert "izaya/izaya.js" not in content
    assert re.search(r'<link rel="stylesheet" href="/static/CACHE/css/output\.\w+\.css"', content)
    # The izaya bundle keeps its defer attribute.
    assert re.search(r'<script src="/static/CACHE/js/output\.\w+\.js" defer></script>', content)
    # Bulma itself is intentionally left outside the compress blocks.
    assert "bulma" in content


def test_assets_are_not_bundled_when_disabled(db, client, settings):
    settings.COMPRESS_ENABLED = False
    resp = client.get(reverse("home"))
    content = resp.content.decode()
    assert "site/css/base.css" in content
    assert "/CACHE/css/" not in content
