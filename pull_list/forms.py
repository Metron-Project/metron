from autocomplete import widgets
from django import forms

from comicsdb.autocomplete import SeriesAutocomplete
from comicsdb.models.series import Series


class AddSeriesToPullListForm(forms.Form):
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
        help_text="Select a series to add to your pull list",
    )
