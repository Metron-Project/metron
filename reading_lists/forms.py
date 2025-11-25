from autocomplete import widgets
from django import forms

from comicsdb.autocomplete import IssueAutocomplete, SeriesAutocomplete
from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from reading_lists.models import ReadingList


class ReadingListForm(forms.ModelForm):
    """Form for creating and editing reading lists."""

    class Meta:
        model = ReadingList
        fields = ("name", "desc", "is_private", "attribution_source", "attribution_url")
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Enter a name for your reading list"}),
            "desc": forms.Textarea(
                attrs={
                    "placeholder": "Describe the reading list (optional)",
                    "rows": 5,
                }
            ),
            "attribution_source": forms.Select(),
            "attribution_url": forms.URLInput(
                attrs={
                    "placeholder": "https://example.com/reading-order",
                    "autocomplete": "url",
                }
            ),
        }
        labels = {
            "desc": "Description",
            "is_private": "Private List",
            "attribution_source": "Source",
            "attribution_url": "Source URL",
        }
        help_texts = {
            "is_private": (
                "Private lists are only visible to you. Public lists can be viewed by anyone."
            ),
            "attribution_source": "Where did you get this reading list from? (optional)",
            "attribution_url": "URL of the specific page for this reading list (optional)",
        }


class AddIssueWithSearchForm(forms.Form):
    """Form for searching and adding issues to a reading list with drag-and-drop ordering."""

    issues = forms.ModelMultipleChoiceField(
        queryset=Issue.objects.select_related("series", "series__series_type").all(),
        required=False,
        widget=widgets.AutocompleteWidget(
            ac_class=IssueAutocomplete,
            attrs={
                "placeholder": "Search for issues...",
                "class": "input",
            },
            options={
                "multiselect": True,
            },
        ),
        label="Search for Issues (Optional)",
        help_text="Add new issues and/or reorder existing issues by dragging",
    )
    issue_order = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Stores the order of selected issues after drag-and-drop",
    )


class AddIssuesFromSeriesForm(forms.Form):
    """Form for adding multiple issues from a series to a reading list."""

    RANGE_CHOICES = [
        ("all", "All issues"),
        ("range", "Issue range"),
    ]

    series = forms.ModelChoiceField(
        queryset=Series.objects.select_related("series_type").all(),
        required=True,
        widget=widgets.AutocompleteWidget(
            ac_class=SeriesAutocomplete,
            attrs={
                "placeholder": "Search for a series...",
                "class": "input",
            },
        ),
        label="Series",
        help_text="Select the series to add issues from",
    )

    range_type = forms.ChoiceField(
        choices=RANGE_CHOICES,
        initial="all",
        widget=forms.RadioSelect(),
        label="What to add",
        required=True,
    )

    start_number = forms.CharField(
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "1", "class": "input"}),
        label="Start Issue #",
        help_text="Leave blank to start from the first issue",
    )

    end_number = forms.CharField(
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "50", "class": "input"}),
        label="End Issue #",
        help_text="Leave blank to go to the last issue",
    )

    position = forms.ChoiceField(
        choices=[
            ("end", "At the end"),
            ("beginning", "At the beginning"),
        ],
        initial="end",
        widget=forms.RadioSelect(),
        label="Add issues",
        required=True,
    )

    def clean(self):
        cleaned_data = super().clean()
        range_type = cleaned_data.get("range_type")
        start_number = cleaned_data.get("start_number")
        end_number = cleaned_data.get("end_number")

        # If range is selected, at least one of start or end must be provided
        if range_type == "range" and not start_number and not end_number:
            raise forms.ValidationError(
                "Please specify at least a start or end issue number for the range."
            )

        return cleaned_data
