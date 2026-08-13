from django import forms
from django.utils.translation import gettext_lazy as _

from comicsdb.autocomplete import IssueAutocomplete, SeriesAutocomplete
from comicsdb.forms.widgets import BulmaMoneyWidget, SafeAutocompleteWidget
from comicsdb.models.series import Series
from user_collection.models import CollectionItem


class CollectionItemForm(forms.ModelForm):
    """Form for creating and editing collection items."""

    class Meta:
        model = CollectionItem
        fields = (
            "issue",
            "quantity",
            "book_format",
            "grade",
            "grading_company",
            "purchase_date",
            "purchase_price",
            "purchase_store",
            "storage_location",
            "notes",
            "is_read",
        )
        widgets = {
            "issue": SafeAutocompleteWidget(
                ac_class=IssueAutocomplete,
                attrs={
                    "placeholder": _("Search for an issue..."),
                    "class": "input",
                },
            ),
            "quantity": forms.NumberInput(attrs={"min": 1, "placeholder": "1"}),
            "book_format": forms.Select(),
            "grade": forms.Select(attrs={"class": "select"}),
            "grading_company": forms.Select(attrs={"class": "select"}),
            "purchase_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "data-bulma-calendar": "on",
                }
            ),
            "purchase_price": BulmaMoneyWidget(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "purchase_store": forms.TextInput(
                attrs={
                    "placeholder": _("Local Comic Shop"),
                }
            ),
            "storage_location": forms.TextInput(
                attrs={
                    "placeholder": _("Long Box 3"),
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "placeholder": _("Additional notes (optional)"),
                    "rows": 4,
                }
            ),
        }
        labels = {
            "book_format": _("Format"),
            "grade": _("Grade"),
            "grading_company": _("Grading Company"),
            "purchase_date": _("Date Purchased"),
            "purchase_price": _("Price Paid"),
            "purchase_store": _("Store/Vendor"),
            "is_read": _("Have you read this issue?"),
        }
        help_texts = {
            "issue": _("Search using 'Series Name (Year) #Number' format."),
            "quantity": _("Number of copies you own"),
            "book_format": _("Physical print, digital, or both"),
            "grade": _("Comic book condition grade (CGC scale)"),
            "grading_company": _("Professional grading company (leave blank if user-assessed)"),
            "purchase_date": _("When did you purchase this issue?"),
            "purchase_price": _("How much did you pay?"),
            "purchase_store": _("Where did you buy it?"),
            "storage_location": _("Where is it stored?"),
            "notes": _("Any additional notes about this item"),
            "is_read": _("Mark this if you've read the issue (read dates managed in detail view)"),
        }

    def __init__(self, *args, **kwargs):
        """Initialize form with user context for validation."""
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_issue(self):
        """Validate that the issue isn't already in the user's collection."""
        issue = self.cleaned_data.get("issue")

        # Only validate on create (not update)
        if (
            not self.instance.pk
            and self.user
            and issue
            and CollectionItem.objects.filter(user=self.user, issue=issue).exists()
        ):
            raise forms.ValidationError(_("This issue is already in your collection."))

        return issue


class AddIssuesFromSeriesForm(forms.Form):
    """Form for adding multiple issues from a series to a collection."""

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
        label=_("Which issues?"),
        help_text=_("Choose whether to add all issues or specify a range"),
    )

    start_number = forms.CharField(
        required=False,
        max_length=25,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("e.g., 1 or 1.1"),
                "class": "input",
            }
        ),
        label=_("Start Issue Number"),
        help_text=_("Optional: Issue number to start from (leave blank to start from beginning)"),
    )

    end_number = forms.CharField(
        required=False,
        max_length=25,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("e.g., 50"),
                "class": "input",
            }
        ),
        label=_("End Issue Number"),
        help_text=_("Optional: Issue number to end at (leave blank to go to end)"),
    )

    default_format = forms.ChoiceField(
        choices=CollectionItem.BookFormat.choices,
        initial=CollectionItem.BookFormat.PRINT,
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        label=_("Default Format"),
        help_text=_("The format to use for all added issues"),
    )

    mark_as_read = forms.BooleanField(
        required=False,
        initial=False,
        label=_("Mark as read"),
        help_text=_("Check this to mark all added issues as read"),
    )
