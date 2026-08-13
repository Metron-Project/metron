from django import forms
from django.utils.translation import gettext_lazy as _

from comicsdb.autocomplete import ArcAutocomplete, IssueAutocomplete, SeriesAutocomplete
from comicsdb.forms.widgets import SafeAutocompleteWidget
from comicsdb.models.arc import Arc
from comicsdb.models.issue import Issue
from comicsdb.models.series import Series
from reading_lists.autocomplete import ReadingListAutocomplete
from reading_lists.models import ReadingList


class ReadingListForm(forms.ModelForm):
    """Form for creating and editing reading lists."""

    previous = forms.ModelChoiceField(
        queryset=ReadingList.objects.all(),
        required=False,
        label=_("Previous List"),
        help_text=_("The reading list that comes before this one in a reading order (optional)"),
        widget=SafeAutocompleteWidget(
            ac_class=ReadingListAutocomplete,
            attrs={"placeholder": _("Search for a reading list..."), "class": "input"},
        ),
    )
    next = forms.ModelChoiceField(
        queryset=ReadingList.objects.all(),
        required=False,
        label=_("Next List"),
        help_text=_("The reading list that comes after this one in a reading order (optional)"),
        widget=SafeAutocompleteWidget(
            ac_class=ReadingListAutocomplete,
            attrs={"placeholder": _("Search for a reading list..."), "class": "input"},
        ),
    )

    class Meta:
        model = ReadingList
        fields = (
            "name",
            "desc",
            "image",
            "is_private",
            "list_type",
            "attribution_source",
            "attribution_url",
            "previous",
            "next",
        )
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _("Enter a name for your reading list")}),
            "image": forms.ClearableFileInput(),
            "desc": forms.Textarea(
                attrs={
                    "placeholder": _("Describe the reading list (optional)"),
                    "rows": 5,
                }
            ),
            "list_type": forms.Select(),
            "attribution_source": forms.Select(),
            "attribution_url": forms.URLInput(
                attrs={
                    "placeholder": "https://example.com/reading-order",
                    "autocomplete": "url",
                }
            ),
        }
        labels = {
            "desc": _("Description"),
            "is_private": _("Private List"),
            "list_type": _("List Type"),
            "attribution_source": _("Source"),
            "attribution_url": _("Source URL"),
        }
        help_texts = {
            "is_private": _(
                "Private lists are only visible to you. Public lists can be viewed by anyone."
            ),
            "attribution_source": _("Where did you get this reading list from? (optional)"),
            "attribution_url": _("URL of the specific page for this reading list (optional)"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A reading list can't link to itself as its own previous/next entry.
        queryset = ReadingList.objects.all()
        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        self.fields["previous"].queryset = queryset
        self.fields["next"].queryset = queryset


class AddIssueWithSearchForm(forms.Form):
    """Form for searching and adding issues to a reading list with drag-and-drop ordering."""

    issues = forms.ModelMultipleChoiceField(
        queryset=Issue.objects.select_related("series", "series__series_type").all(),
        required=False,
        widget=SafeAutocompleteWidget(
            ac_class=IssueAutocomplete,
            attrs={
                "placeholder": _("Search for issues..."),
                "class": "input",
            },
            options={
                "multiselect": True,
            },
        ),
        label=_("Search for Issues (Optional)"),
        help_text=_("Add new issues and/or reorder existing issues by dragging"),
    )
    issue_order = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text=_("Stores the order of selected issues after drag-and-drop"),
    )


class AddIssuesFromSeriesForm(forms.Form):
    """Form for adding multiple issues from a series to a reading list."""

    RANGE_CHOICES = [
        ("all", _("All issues")),
        ("range", _("Issue range")),
    ]

    series = forms.ModelChoiceField(
        queryset=Series.objects.select_related("series_type").all(),
        required=True,
        widget=SafeAutocompleteWidget(
            ac_class=SeriesAutocomplete,
            attrs={
                "placeholder": _("Search for a series..."),
                "class": "input",
            },
        ),
        label=_("Series"),
        help_text=_("Select the series to add issues from"),
    )

    range_type = forms.ChoiceField(
        choices=RANGE_CHOICES,
        initial="all",
        widget=forms.RadioSelect(),
        label=_("What to add"),
        required=True,
    )

    start_number = forms.CharField(
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "1", "class": "input"}),
        label=_("Start Issue #"),
        help_text=_("Leave blank to start from the first issue"),
    )

    end_number = forms.CharField(
        max_length=25,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "50", "class": "input"}),
        label=_("End Issue #"),
        help_text=_("Leave blank to go to the last issue"),
    )

    position = forms.ChoiceField(
        choices=[
            ("end", _("At the end")),
            ("beginning", _("At the beginning")),
        ],
        initial="end",
        widget=forms.RadioSelect(),
        label=_("Add issues"),
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
                _("Please specify at least a start or end issue number for the range.")
            )

        return cleaned_data


class AddIssuesFromArcForm(forms.Form):
    """Form for adding all issues from a story arc to a reading list."""

    arc = forms.ModelChoiceField(
        queryset=Arc.objects.all(),
        required=True,
        widget=SafeAutocompleteWidget(
            ac_class=ArcAutocomplete,
            attrs={
                "placeholder": _("Search for a story arc..."),
                "class": "input",
            },
        ),
        label=_("Story Arc"),
        help_text=_("Select the story arc to add issues from"),
    )

    position = forms.ChoiceField(
        choices=[
            ("end", _("At the end")),
            ("beginning", _("At the beginning")),
        ],
        initial="end",
        widget=forms.RadioSelect(),
        label=_("Add issues"),
        required=True,
    )
