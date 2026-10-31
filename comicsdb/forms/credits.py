from django.forms import (
    ModelChoiceField,
    ModelForm,
    ModelMultipleChoiceField,
    inlineformset_factory,
)
from django.utils.translation import gettext_lazy as _
from izaya import LookupWidget

from comicsdb.lookups import CreatorLookup, RoleLookup
from comicsdb.models import Creator, Credits, Issue
from comicsdb.models.credits import Role


class CreditsForm(ModelForm):
    creator = ModelChoiceField(
        queryset=Creator.objects.all(),
        widget=LookupWidget(CreatorLookup, attrs={"placeholder": _("Autocomplete...")}),
    )
    role = ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=LookupWidget(RoleLookup, multiple=True),
    )

    class Meta:
        model = Credits
        fields = ["issue", "creator", "role"]


CreditsFormSet = inlineformset_factory(Issue, Credits, form=CreditsForm, extra=1, can_delete=True)
