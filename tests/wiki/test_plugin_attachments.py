"""Tests for the wiki attachments plugin."""

import pytest
from django.contrib.auth.models import AnonymousUser

from wiki.plugins.attachments.models import (
    Attachment,
    IllegalFileExtension,
    extension_allowed,
)

pytestmark = pytest.mark.django_db


class TestExtensionAllowed:
    """Tests for the extension_allowed() helper function."""

    def test_valid_extension_returns_extension(self):
        """Allowed extensions are returned as-is."""
        assert extension_allowed("document.pdf") == "pdf"

    def test_valid_extension_case_insensitive(self):
        """Extension matching is case-insensitive."""
        assert extension_allowed("report.PDF") == "PDF"

    def test_valid_txt_extension(self):
        """Plain text files are allowed."""
        assert extension_allowed("readme.txt") == "txt"

    def test_invalid_extension_raises(self):
        """Disallowed file extensions raise IllegalFileExtension."""
        with pytest.raises(IllegalFileExtension):
            extension_allowed("script.exe")

    def test_invalid_extension_py_raises(self):
        """Python files are not allowed as attachments."""
        with pytest.raises(IllegalFileExtension):
            extension_allowed("exploit.py")

    def test_no_extension_raises(self):
        """A filename with no extension raises IllegalFileExtension."""
        with pytest.raises(IllegalFileExtension):
            extension_allowed("no_extension_file")

    def test_dotfile_no_extension_raises(self):
        """A dotfile without a real extension (e.g. '.hidden') raises."""
        with pytest.raises(IllegalFileExtension):
            extension_allowed(".hidden")


class TestAttachmentModel:
    """Tests for the Attachment model."""

    def test_attachment_can_write_anonymous_denied(self, wiki_root):
        """Anonymous users cannot write to attachments by default."""
        attachment = Attachment()
        attachment.article = wiki_root.article
        # Attachment.can_write() checks ANONYMOUS setting before delegating
        user = AnonymousUser()
        assert attachment.can_write(user) is False

    def test_attachment_can_delete_mirrors_can_write(self, wiki_root, wiki_user):
        """can_delete() delegates to can_write()."""
        attachment = Attachment()
        attachment.article = wiki_root.article
        # A regular user who can write can also delete
        assert attachment.can_delete(wiki_user) == attachment.can_write(wiki_user)

    def test_attachment_str_no_article(self):
        """__str__() on an unsaved attachment handles missing article gracefully."""
        attachment = Attachment()
        # Should not raise — returns a fallback string
        result = str(attachment)
        assert isinstance(result, str)
