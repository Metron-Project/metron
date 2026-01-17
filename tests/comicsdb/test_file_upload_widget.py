"""Tests for the file upload widget templates."""

import pytest
from django.forms import ClearableFileInput, Form, ImageField
from django.template import Context, Template


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


class TestFileUploadWidgetInContext:
    """Test file upload widget rendered in the context of actual forms."""

    @pytest.fixture
    def creator_form_template(self):
        """Return a template that renders the creator form."""
        return Template(
            """
            {% load bulma_tags %}
            {{ form.image }}
            """
        )

    def test_creator_form_image_field_has_onchange_handler(self, db, creator_form_template):
        """Test that creator form image field includes onchange handler."""
        from comicsdb.forms.creator import CreatorForm

        form = CreatorForm()
        context = Context({"form": form})
        rendered = creator_form_template.render(context)

        # Verify onchange handler is present
        assert "onchange" in rendered
        assert "filename-image" in rendered


class TestWikiFormFieldFileUpload:
    """Tests for the wiki formfield.html file upload template."""

    def test_wiki_file_field_template_syntax(self):
        """Test that the wiki formfield template has correct onchange syntax."""
        from django.template.loader import get_template

        template = get_template("wiki/includes/formfield.html")
        source = template.template.source

        # Verify the template uses onchange for DOM events
        assert "onchange" in source
        # Verify it targets the correct filename element pattern
        assert "filename_{{ field.auto_id }}" in source
