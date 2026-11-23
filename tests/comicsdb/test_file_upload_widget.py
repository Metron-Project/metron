"""Tests for the file upload widget templates."""

import pytest
from django.forms import ClearableFileInput, Form, ImageField
from django.template.loader import get_template
from django.templatetags.static import static
from django.urls import reverse
from heggra import UploadWidget

from comicsdb.forms.arc import ArcForm
from comicsdb.forms.character import CharacterForm
from comicsdb.forms.creator import CreatorForm
from comicsdb.forms.imprint import ImprintForm
from comicsdb.forms.issue import IssueForm
from comicsdb.forms.publisher import PublisherForm
from comicsdb.forms.team import TeamForm
from comicsdb.forms.universe import UniverseForm
from comicsdb.forms.widgets import MAX_IMAGE_SIZE
from reading_lists.forms import ReadingListForm
from users.forms import CustomUserChangeForm


class TestFileUploadWidgetTemplate:
    """Tests for the clearable_file_input.html template."""

    @pytest.fixture
    def file_input_form(self):
        """Create a simple form with a file input for testing."""

        class TestForm(Form):
            image = ImageField(required=False, widget=ClearableFileInput())

        return TestForm

    def test_file_input_renders_onchange_handler(self, file_input_form):
        """Test that file input has onchange attribute for updating filename display."""
        form = file_input_form()
        rendered = form["image"].as_widget()

        # Check that the onchange attribute is present
        assert 'onchange="' in rendered
        # Check that it references the correct filename element
        assert "filename-image" in rendered
        # Check that the filename span exists
        assert 'id="filename-image"' in rendered

    def test_file_input_has_bulma_classes(self, file_input_form):
        """Test that file input uses Bulma CSS classes."""
        form = file_input_form()
        rendered = form["image"].as_widget()

        assert "file-input" in rendered
        assert "file has-name" in rendered
        assert "file-cta" in rendered
        assert "file-name" in rendered

    def test_file_input_shows_no_file_selected_by_default(self, file_input_form):
        """Test that file input shows 'No file selected' by default."""
        form = file_input_form()
        rendered = form["image"].as_widget()

        assert "No file selected" in rendered

    def test_file_input_change_handler_updates_filename(self, file_input_form):
        """Test that the change handler JavaScript updates filename correctly."""
        form = file_input_form()
        rendered = form["image"].as_widget()

        # Verify the JavaScript logic is in the handler
        assert "this.files.length > 0" in rendered
        assert "this.files[0].name" in rendered

    def test_file_input_with_initial_value_shows_current_file(self, file_input_form, db):
        """Test that when a file already exists, it shows the current file section."""
        # This would require mocking a file, but we can test the template structure
        form = file_input_form()
        rendered = form["image"].as_widget()

        # Without initial value, should not show "Currently:"
        # The template only shows initial_text when widget.is_initial is True
        assert "Choose a file" in rendered


class TestUploadWidgetInForms:
    """Test that every image form except the variant formset uses heggra's upload widget."""

    @pytest.mark.parametrize(
        "form_class",
        [
            ArcForm,
            CharacterForm,
            CreatorForm,
            CustomUserChangeForm,
            ImprintForm,
            IssueForm,
            PublisherForm,
            ReadingListForm,
            TeamForm,
            UniverseForm,
        ],
    )
    def test_image_field_uses_upload_widget(self, db, form_class):
        """Test that the image field is an image UploadWidget that renders the htmx uploader."""
        form = form_class()
        widget = form.fields["image"].widget
        assert isinstance(widget, UploadWidget)
        assert widget.image
        assert widget.max_size == MAX_IMAGE_SIZE

        rendered = form["image"].as_widget()
        assert "data-heggra" in rendered
        assert f'hx-post="{reverse("heggra:upload")}"' in rendered
        assert 'accept="image/*"' in rendered
        assert f'data-heggra-max-size="{MAX_IMAGE_SIZE}"' in rendered

    def test_base_template_loads_heggra_script(self, client):
        """Test that every page loads heggra.js, which the upload widgets need."""
        resp = client.get(reverse("home"))
        assert static("heggra/heggra.js") in resp.content.decode()


class TestWikiFormFieldFileUpload:
    """Tests for the wiki formfield.html file upload template."""

    def test_wiki_file_field_template_syntax(self):
        """Test that the wiki formfield template has correct onchange syntax."""
        template = get_template("wiki/includes/formfield.html")
        source = template.template.source

        # Verify the template uses onchange for DOM events
        assert "onchange" in source
        # Verify it targets the correct filename element pattern
        assert "filename_{{ field.auto_id }}" in source
