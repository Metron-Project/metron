"""Tests for the per-user limit on heggra uploads."""

import io
import json
from unittest.mock import patch

import heggra.views
import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from comicsdb.forms.widgets import ImageUploadWidget
from metron import heggra_urls

LIMIT = 2


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.fixture
def low_limit():
    with patch("metron.heggra_urls.UPLOAD_LIMIT", LIMIT):
        yield


def _post_image(client, widget=None):
    """Post an image to the upload view the way ``widget`` does."""
    widget = widget or ImageUploadWidget()
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


def test_limit_error_uses_the_widget_classes(media_root, low_limit, auto_login_user):
    """Like heggra's own errors, the limit's message is styled with the posting widget's classes."""
    client, _ = auto_login_user()
    for _attempt in range(LIMIT):
        _post_image(client)

    resp = _post_image(client, ImageUploadWidget(classes={"error": "notification is-danger"}))

    assert resp.status_code == 429
    assert 'class="heggra-error notification is-danger"' in resp.content.decode()


def test_limit_error_without_a_valid_config_uses_the_setting(
    media_root, low_limit, auto_login_user, settings
):
    client, _ = auto_login_user()
    for _attempt in range(LIMIT):
        _post_image(client)

    resp = client.post(reverse("heggra:upload"), {"heggra-config": "forged"})

    assert resp.status_code == 429
    assert f'class="heggra-error {settings.HEGGRA_CLASSES["error"]}"' in resp.content.decode()


def test_refused_uploads_do_not_count(media_root, low_limit, auto_login_user):
    client, _ = auto_login_user()
    widget = ImageUploadWidget()
    hx_vals = json.loads(widget.get_context("image", None, {})["widget"]["hx_vals"])
    for _attempt in range(LIMIT + 1):
        not_an_image = SimpleUploadedFile("cover.png", b"not an image", content_type="image/png")
        resp = client.post(reverse("heggra:upload"), {**hx_vals, "image": not_an_image})
        assert resp.status_code == 422

    assert _post_image(client).status_code == 200


def test_simultaneous_uploads_cannot_pass_the_limit(media_root, low_limit, auto_login_user):
    """An upload that arrives while another is still being saved sees that one's slot taken."""
    client, _ = auto_login_user()
    for _attempt in range(LIMIT - 1):
        _post_image(client)
    save_upload = heggra.views.upload
    arrived_meanwhile = []

    def save_while_another_arrives(request):
        if not arrived_meanwhile:
            arrived_meanwhile.append(_post_image(client))
        return save_upload(request)

    with patch("heggra.views.upload", save_while_another_arrives):
        first = _post_image(client)

    assert first.status_code == 200
    assert arrived_meanwhile[0].status_code == 429


def test_refused_uploads_give_their_slot_back(media_root, low_limit, auto_login_user):
    client, user = auto_login_user()
    for _attempt in range(LIMIT):
        _post_image(client)
    for _attempt in range(3):
        _post_image(client)

    # Over-limit attempts don't pile up, so the window only holds the saved uploads.
    assert cache.get(heggra_urls._key(user)) == LIMIT


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
