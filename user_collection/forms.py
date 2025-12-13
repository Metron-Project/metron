from autocomplete import widgets
from django import forms

from comicsdb.autocomplete import IssueAutocomplete, SeriesAutocomplete
from comicsdb.forms.widgets import BulmaMoneyWidget
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
            "date_read",
        )
        widgets = {
            "issue": widgets.AutocompleteWidget(
                ac_class=IssueAutocomplete,
                attrs={
                    "placeholder": "Search for an issue...",
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
                    "placeholder": "Local Comic Shop",
                }
            ),
            "storage_location": forms.TextInput(
                attrs={
                    "placeholder": "Long Box 3",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "placeholder": "Additional notes (optional)",
                    "rows": 4,
                }
            ),
            "date_read": forms.DateInput(
                attrs={
                    "type": "date",
                    "data-bulma-calendar": "on",
                }
            ),
        }
        labels = {
            "book_format": "Format",
            "grade": "Grade",
            "grading_company": "Grading Company",
            "purchase_date": "Date Purchased",
            "purchase_price": "Price Paid",
            "purchase_store": "Store/Vendor",
            "is_read": "Have you read this issue?",
            "date_read": "Date Read",
        }
        help_texts = {
            "quantity": "Number of copies you own",
            "book_format": "Physical print, digital, or both",
            "grade": "Comic book condition grade (CGC scale)",
            "grading_company": "Professional grading company (leave blank if user-assessed)",
            "purchase_date": "When did you purchase this issue?",
            "purchase_price": "How much did you pay?",
            "purchase_store": "Where did you buy it?",
            "storage_location": "Where is it stored?",
            "notes": "Any additional notes about this item",
            "is_read": "Mark this if you've read the issue",
            "date_read": "When did you read this issue?",
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
            raise forms.ValidationError("This issue is already in your collection.")

        return issue


class AddIssuesFromSeriesForm(forms.Form):
    """Form for adding multiple issues from a series to a collection."""

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
        label="Which issues?",
        help_text="Choose whether to add all issues or specify a range",
    )

    start_number = forms.CharField(
        required=False,
        max_length=25,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g., 1 or 1.1",
                "class": "input",
            }
        ),
        label="Start Issue Number",
        help_text="Optional: Issue number to start from (leave blank to start from beginning)",
    )

    end_number = forms.CharField(
        required=False,
        max_length=25,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g., 50",
                "class": "input",
            }
        ),
        label="End Issue Number",
        help_text="Optional: Issue number to end at (leave blank to go to end)",
    )

    default_format = forms.ChoiceField(
        choices=CollectionItem.BookFormat.choices,
        initial=CollectionItem.BookFormat.PRINT,
        required=False,
        widget=forms.Select(attrs={"class": "select"}),
        label="Default Format",
        help_text="The format to use for all added issues",
    )

    mark_as_read = forms.BooleanField(
        required=False,
        initial=False,
        label="Mark as read",
        help_text="Check this to mark all added issues as read",
    )
