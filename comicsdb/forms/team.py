from django.forms import ModelForm
from heggra import UploadWidget
from izaya import LookupWidget

from comicsdb.forms.creator import CreatorsWidget
from comicsdb.forms.universe import UniversesWidget
from comicsdb.lookups import TeamLookup
from comicsdb.models import Team

TeamsWidget = LookupWidget(TeamLookup, multiple=True)


class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = ("name", "desc", "creators", "universes", "cv_id", "gcd_id", "image")
        widgets = {
            "creators": CreatorsWidget,
            "universes": UniversesWidget,
            "image": UploadWidget(image=True),
        }
