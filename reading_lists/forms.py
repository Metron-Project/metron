from autocomplete import widgets
from django import forms

from comicsdb.models.issue import Issue
from reading_lists.autocomplete import IssueAutocomplete
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
