"""Tests for the wiki images plugin."""

import markdown
import pytest
from django.contrib.auth.models import AnonymousUser

from wiki.plugins.images.markdown_extensions import ImagePostprocessor
from wiki.plugins.images.models import Image

pytestmark = pytest.mark.django_db


class TestImagePostprocessor:
    """Tests for the ImagePostprocessor markdown post-processor."""

    def _make_postprocessor(self):
        """Create a minimal ImagePostprocessor without a real markdown instance."""

        md = markdown.Markdown()
        return ImagePostprocessor(md)

    def test_unwraps_figure_from_paragraph(self):
        """The postprocessor removes the <p> wrapper that Markdown adds around <figure>."""
        pp = self._make_postprocessor()
        html = "<p><figure><img src='x.jpg'></figure>\n</p>"
        result = pp.run(html)
        assert result == "<figure><img src='x.jpg'></figure>"

    def test_leaves_non_figure_content_unchanged(self):
        """Regular paragraph content is not touched."""
        pp = self._make_postprocessor()
        html = "<p>Just some text.</p>"
        assert pp.run(html) == html

    def test_multiple_figures_unwrapped(self):
        """Multiple figure/paragraph pairs are all cleaned up."""
        pp = self._make_postprocessor()
        html = "<p><figure>A</figure>\n</p><p><figure>B</figure>\n</p>"
        result = pp.run(html)
        assert "<p><figure" not in result
        assert "</figure>\n</p>" not in result


class TestImageModel:
    """Tests for the Image model."""

    def test_image_can_write_anonymous_denied(self, wiki_root):
        """Anonymous users cannot write to images by default."""
        image = Image()
        image.article = wiki_root.article
        assert image.can_write(AnonymousUser()) is False

    def test_image_can_delete_mirrors_can_write(self, wiki_root, wiki_user):
        """can_delete() delegates to can_write()."""
        image = Image()
        image.article = wiki_root.article
        assert image.can_delete(wiki_user) == image.can_write(wiki_user)

    def test_image_str_without_revision(self):
        """__str__() on an image without a current revision returns a fallback."""
        image = Image()
        result = str(image)
        assert "revision" in result.lower() or "image" in result.lower()
