from django import forms
from django.utils.translation import gettext_lazy as _

from comicsdb.autocomplete import SeriesAutocomplete
from comicsdb.forms.widgets import SafeAutocompleteWidget
from comicsdb.models.series import Series


class AddSeriesToPullListForm(forms.Form):
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
        help_text=_("Select a series to add to your pull list"),
    )
