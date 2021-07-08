from dal import autocomplete
from django.forms import ModelChoiceField, ModelForm, inlineformset_factory

from comicsdb.models import Creator, Credits, Issue


class CreditsForm(ModelForm):
    creator = ModelChoiceField(
        queryset=Creator.objects.all(),
        widget=autocomplete.ModelSelect2(
            url="issue:creator-autocomplete",
            attrs={
                "data-placeholder": "Autocomplete...",
                "data-minimum-input-length": 3,
            },
        ),
    )

    class Meta:
        model = Credits
        fields = "__all__"


CreditsFormSet = inlineformset_factory(
    Issue, Credits, form=CreditsForm, extra=1, can_delete=True
)
