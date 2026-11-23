"""Tests for the per-user limit on heggra uploads."""

import io
import json
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from comicsdb.forms.widgets import ImageUploadWidget

LIMIT = 2


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def low_limit():
    with patch("metron.heggra_urls.UPLOAD_LIMIT", LIMIT):
        yield


def _post_image(client):
    """Post an image to the upload view the way the widget does."""
    widget = ImageUploadWidget()
    hx_vals = json.loads(widget.get_context("image", None, {})["widget"]["hx_vals"])
    buffer = io.BytesIO()
    Image.new("RGB", (30, 45), "red").save(buffer, "PNG")
    image = SimpleUploadedFile("cover.png", buffer.getvalue(), content_type="image/png")
    return client.post(reverse("heggra:upload"), {**hx_vals, "image": image})


def test_uploads_within_the_limit_are_saved(media_root, low_limit, auto_login_user):
    client, _ = auto_login_user()
    for _attempt in range(LIMIT):
        resp = _post_image(client)
        assert resp.status_code == 200
        assert resp.headers["X-Heggra-Upload"] == "true"
    assert len(list((media_root / "heggra").iterdir())) == LIMIT


def test_upload_over_the_limit_is_refused(media_root, low_limit, auto_login_user):
    client, _ = auto_login_user()
    for _attempt in range(LIMIT):
        _post_image(client)

    resp = _post_image(client)

    assert resp.status_code == 429
    assert resp.headers["X-Heggra-Error"] == "true"
    assert "too many files" in resp.content.decode()
    assert len(list((media_root / "heggra").iterdir())) == LIMIT


def test_limit_is_per_user(media_root, low_limit, client, create_user, test_password):
    first, second = create_user(), create_user()
    client.login(username=first.username, password=test_password)
    for _attempt in range(LIMIT + 1):
        _post_image(client)

    client.login(username=second.username, password=test_password)

    assert _post_image(client).status_code == 200


def test_staff_are_not_limited(media_root, low_limit, client, create_staff_user, test_password):
    client.login(username=create_staff_user.username, password=test_password)
    for _attempt in range(LIMIT + 1):
        assert _post_image(client).status_code == 200


def test_anonymous_upload_is_refused_by_heggra(media_root, client):
    resp = _post_image(client)

    assert resp.status_code == 403
    assert not (media_root / "heggra").exists()
