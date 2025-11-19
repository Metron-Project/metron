from autocomplete import widgets
from django.forms import ModelChoiceField, ModelForm, SelectMultiple, inlineformset_factory

from comicsdb.autocomplete import CreatorAutocomplete
from comicsdb.models import Creator, Credits, Issue


class CreditsForm(ModelForm):
    creator = ModelChoiceField(
        queryset=Creator.objects.all(),
        widget=widgets.AutocompleteWidget(
            ac_class=CreatorAutocomplete,
            attrs={
                "placeholder": "Autocomplete...",
            },
        ),
    )

    class Meta:
        model = Credits
        fields = ["issue", "creator", "role"]
        widgets = {"role": SelectMultiple(attrs={"size": 5})}


CreditsFormSet = inlineformset_factory(Issue, Credits, form=CreditsForm, extra=1, can_delete=True)
