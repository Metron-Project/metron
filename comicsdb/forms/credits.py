from django.forms import (
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    inlineformset_factory,
)

from comicsdb.autocomplete import CreatorAutocomplete, RoleAutocomplete
from comicsdb.forms.widgets import SafeAutocompleteWidget
from comicsdb.models import Creator, Credits, Issue
from comicsdb.models.credits import Role


class CreditsForm(ModelForm):
    creator = ModelChoiceField(
        queryset=Creator.objects.all(),
        widget=SafeAutocompleteWidget(
            ac_class=CreatorAutocomplete,
            attrs={
                "placeholder": "Autocomplete...",
            },
        ),
    )
    role = ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=SafeAutocompleteWidget(
            ac_class=RoleAutocomplete,
            attrs={"class": "input"},
            options={"multiselect": True},
        ),
    )

    class Meta:
        model = Credits
        fields = ["issue", "creator", "role"]


CreditsFormSet = inlineformset_factory(Issue, Credits, form=CreditsForm, extra=1, can_delete=True)
