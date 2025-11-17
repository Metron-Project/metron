"""Tests for reading_lists forms."""

from reading_lists.forms import AddIssueWithSearchForm, ReadingListForm
from reading_lists.models import ReadingList


class TestReadingListForm:
    """Tests for the ReadingListForm."""

    def test_reading_list_form_valid_data(self):
        """Test form with valid data."""
        form_data = {
            "name": "Test Reading List",
            "desc": "A test reading list",
            "is_private": False,
            "attribution_source": "",
            "attribution_url": "",
        }
        form = ReadingListForm(data=form_data)
        assert form.is_valid()

    def test_reading_list_form_valid_with_attribution(self):
        """Test form with valid data including attribution."""
        form_data = {
            "name": "Test Reading List",
            "desc": "A test reading list",
            "is_private": False,
            "attribution_source": ReadingList.AttributionSource.CBRO,
            "attribution_url": "https://example.com/reading-order",
        }
        form = ReadingListForm(data=form_data)
        assert form.is_valid()

    def test_reading_list_form_missing_name(self):
        """Test form with missing required name field."""
        form_data = {
            "desc": "A test reading list",
            "is_private": False,
        }
        form = ReadingListForm(data=form_data)
        assert not form.is_valid()
        assert "name" in form.errors

    def test_reading_list_form_optional_desc(self):
        """Test form with missing optional desc field."""
        form_data = {
            "name": "Test Reading List",
            "is_private": False,
        }
        form = ReadingListForm(data=form_data)
        assert form.is_valid()

    def test_reading_list_form_private_default(self):
        """Test that is_private defaults to False."""
        form_data = {
            "name": "Test Reading List",
        }
        form = ReadingListForm(data=form_data)
        assert form.is_valid()
        # Check that is_private is False by default
        assert not form.cleaned_data["is_private"]

    def test_reading_list_form_fields(self):
        """Test that form has the correct fields."""
        form = ReadingListForm()
        expected_fields = ["name", "desc", "is_private", "attribution_source", "attribution_url"]
        assert list(form.fields.keys()) == expected_fields

    def test_reading_list_form_widgets(self):
        """Test that form uses the correct widgets."""
        form = ReadingListForm()
        assert (
            form.fields["name"].widget.attrs["placeholder"] == "Enter a name for your reading list"
        )
        assert (
            form.fields["desc"].widget.attrs["placeholder"]
            == "Describe the reading list (optional)"
        )
        assert form.fields["desc"].widget.attrs["rows"] == 5
        assert (
            form.fields["attribution_url"].widget.attrs["placeholder"]
            == "https://example.com/reading-order"
        )

    def test_reading_list_form_labels(self):
        """Test that form has the correct labels."""
        form = ReadingListForm()
        assert form.fields["desc"].label == "Description"
        assert form.fields["is_private"].label == "Private List"
        assert form.fields["attribution_source"].label == "Source"
        assert form.fields["attribution_url"].label == "Source URL"

    def test_reading_list_form_help_texts(self):
        """Test that form has the correct help texts."""
        form = ReadingListForm()
        assert "Private lists are only visible to you" in form.fields["is_private"].help_text
        assert (
            "Where did you get this reading list from?"
            in form.fields["attribution_source"].help_text
        )
        assert (
            "URL of the specific page for this reading list"
            in form.fields["attribution_url"].help_text
        )

    def test_reading_list_form_invalid_url(self):
        """Test form with invalid attribution URL."""
        form_data = {
            "name": "Test Reading List",
            "desc": "A test reading list",
            "is_private": False,
            "attribution_source": ReadingList.AttributionSource.CBRO,
            "attribution_url": "not-a-valid-url",
        }
        form = ReadingListForm(data=form_data)
        assert not form.is_valid()
        assert "attribution_url" in form.errors


class TestAddIssueWithSearchForm:
    """Tests for the AddIssueWithSearchForm."""

    def test_add_issue_form_empty(self):
        """Test form with empty data."""
        form_data = {
            "issues": [],
            "issue_order": "",
        }
        form = AddIssueWithSearchForm(data=form_data)
        assert form.is_valid()

    def test_add_issue_form_with_issues(self, reading_list_issue_1, reading_list_issue_2):
        """Test form with issues selected."""
        form_data = {
            "issues": [reading_list_issue_1.pk, reading_list_issue_2.pk],
            "issue_order": f"{reading_list_issue_1.pk},{reading_list_issue_2.pk}",
        }
        form = AddIssueWithSearchForm(data=form_data)
        assert form.is_valid()
        assert len(form.cleaned_data["issues"]) == 2

    def test_add_issue_form_with_order_only(self, reading_list_issue_1, reading_list_issue_2):
        """Test form with only issue_order specified."""
        form_data = {
            "issues": [],
            "issue_order": f"{reading_list_issue_1.pk},{reading_list_issue_2.pk}",
        }
        form = AddIssueWithSearchForm(data=form_data)
        assert form.is_valid()
        assert (
            form.cleaned_data["issue_order"]
            == f"{reading_list_issue_1.pk},{reading_list_issue_2.pk}"
        )

    def test_add_issue_form_fields(self):
        """Test that form has the correct fields."""
        form = AddIssueWithSearchForm()
        expected_fields = ["issues", "issue_order"]
        assert list(form.fields.keys()) == expected_fields

    def test_add_issue_form_issues_not_required(self):
        """Test that issues field is not required."""
        form = AddIssueWithSearchForm()
        assert not form.fields["issues"].required

    def test_add_issue_form_issue_order_not_required(self):
        """Test that issue_order field is not required."""
        form = AddIssueWithSearchForm()
        assert not form.fields["issue_order"].required

    def test_add_issue_form_labels(self):
        """Test that form has the correct labels."""
        form = AddIssueWithSearchForm()
        assert form.fields["issues"].label == "Search for Issues (Optional)"

    def test_add_issue_form_help_texts(self):
        """Test that form has the correct help texts."""
        form = AddIssueWithSearchForm()
        assert (
            "Add new issues and/or reorder existing issues by dragging"
            in form.fields["issues"].help_text
        )
        assert (
            "Stores the order of selected issues after drag-and-drop"
            in form.fields["issue_order"].help_text
        )

    def test_add_issue_form_invalid_issue_ids(self, db):
        """Test form with invalid issue IDs."""
        form_data = {
            "issues": [99999],  # Non-existent issue ID
            "issue_order": "99999",
        }
        form = AddIssueWithSearchForm(data=form_data)
        assert not form.is_valid()
        assert "issues" in form.errors
