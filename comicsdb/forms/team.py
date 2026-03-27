from django.forms import ClearableFileInput, ModelForm

from comicsdb.autocomplete import TeamAutocomplete
from comicsdb.forms.creator import CreatorsWidget
from comicsdb.forms.universe import UniversesWidget
from comicsdb.forms.widgets import SafeAutocompleteWidget
from comicsdb.models import Team

TeamsWidget = SafeAutocompleteWidget(
    ac_class=TeamAutocomplete,
    attrs={"class": "input"},
    options={"multiselect": True},
)


class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = ("name", "desc", "creators", "universes", "cv_id", "gcd_id", "image")
        widgets = {
            "creators": CreatorsWidget,
            "universes": UniversesWidget,
            "image": ClearableFileInput(),
        }
