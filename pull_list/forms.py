from autocomplete import widgets
from django import forms

from comicsdb.autocomplete import SeriesAutocomplete
from comicsdb.models.series import Series
from pull_list.models import PullList


class PullListSettingsForm(forms.ModelForm):
    class Meta:
        model = PullList
        fields = ("is_private",)
        labels = {
            "is_private": "Private Pull List",
        }
        help_texts = {
            "is_private": (
                "Private pull lists are only visible to you. "
                "Public pull lists can be viewed by anyone."
            ),
        }


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
