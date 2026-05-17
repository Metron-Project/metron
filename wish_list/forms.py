from autocomplete import widgets
from django import forms

from comicsdb.autocomplete import IssueAutocomplete
from comicsdb.forms.widgets import BulmaMoneyWidget
from wish_list.models import WishList, WishListItem


class WishListSettingsForm(forms.ModelForm):
    class Meta:
        model = WishList
        fields = ("is_private",)
        labels = {
            "is_private": "Private Wish List",
        }
        help_texts = {
            "is_private": (
                "Private wish lists are only visible to you. "
                "Public wish lists can be viewed by anyone."
            ),
        }


class WishListItemForm(forms.ModelForm):
    class Meta:
        model = WishListItem
        fields = (
            "issue",
            "priority",
            "status",
            "desired_grade",
            "max_price",
            "notes",
        )
        widgets = {
            "issue": widgets.AutocompleteWidget(
                ac_class=IssueAutocomplete,
                attrs={
                    "placeholder": "Search for an issue...",
                    "class": "input",
                },
            ),
            "priority": forms.Select(),
            "status": forms.Select(),
            "desired_grade": forms.Select(attrs={"class": "select"}),
            "max_price": BulmaMoneyWidget(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "0.00",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "placeholder": "Notes about this item (optional)",
                    "rows": 4,
                }
            ),
        }
        labels = {
            "desired_grade": "Minimum Grade",
            "max_price": "Maximum Price",
            "priority": "Priority (1=Highest)",
        }
        help_texts = {
            "issue": "Search using 'Series Name (Year) #Number' format.",
            "desired_grade": "Leave blank if any condition is acceptable.",
            "priority": "1 is highest priority, 5 is lowest.",
        }


class AcquireWishListItemForm(forms.Form):
    purchase_date = forms.DateField(
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "data-bulma-calendar": "on",
            }
        ),
        label="Purchase Date",
    )
    purchase_price = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "0.00"}),
        label="Price Paid",
    )
    purchase_store = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Local Comic Shop"}),
        label="Store/Vendor",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"placeholder": "Additional notes", "rows": 3}),
        label="Notes",
    )
