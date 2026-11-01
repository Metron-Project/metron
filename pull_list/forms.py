from django import forms
from django.utils.translation import gettext_lazy as _
from izaya import LookupWidget

from comicsdb.lookups import SeriesLookup
from comicsdb.models.series import Series


class AddSeriesToPullListForm(forms.Form):
    series = forms.ModelChoiceField(
        queryset=Series.objects.select_related("series_type").all(),
        required=True,
        widget=LookupWidget(SeriesLookup, attrs={"placeholder": _("Search for a series...")}),
        label=_("Series"),
        help_text=_("Select a series to add to your pull list"),
    )
