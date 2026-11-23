"""Tests for saving an issue cover uploaded ahead of the form through heggra."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from heggra.storage import save_temporary
from PIL import Image

from comicsdb.forms.issue import IssueForm
from comicsdb.models import Rating


def _cover() -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new("RGB", (300, 450), "red").save(buffer, "PNG")
    return SimpleUploadedFile("cover.png", buffer.getvalue(), content_type="image/png")


@pytest.fixture
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


@pytest.mark.django_db
def test_pending_cover_is_saved_and_hashed(media_root, fc_series, create_user):
    user = create_user()
    form = IssueForm()
    upload = save_temporary(_cover(), form.fields["image"].widget.rules("image"))
    data = {
        "series": fc_series.id,
        "number": "1",
        "cover_date": "2023-01-01",
        "rating": Rating.objects.create(name="Test Rating").id,
        "image-token": upload.token,
    }

    form = IssueForm(data=data)
    assert form.is_valid(), form.errors
    issue = form.save(commit=False)
    issue.created_by = issue.edited_by = user
    issue.save()

    assert issue.image.name.startswith("issue/")
    assert (media_root / issue.image.name).is_file()
    assert issue.cover_hash


@pytest.mark.django_db
def test_invalid_cover_token_is_an_error(media_root, fc_series):
    data = {
        "series": fc_series.id,
        "number": "1",
        "cover_date": "2023-01-01",
        "rating": Rating.objects.create(name="Test Rating").id,
        "image-token": "not-a-valid-token",
    }

    form = IssueForm(data=data)

    assert not form.is_valid()
    assert "image" in form.errors
