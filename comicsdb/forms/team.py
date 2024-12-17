from django.forms import ClearableFileInput, ModelForm
from django_select2 import forms as s2forms

from comicsdb.forms.creator import CreatorsWidget
from comicsdb.forms.universe import UniversesWidget
from comicsdb.models import Team


class TeamsWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = ["name__icontains"]


class TeamForm(ModelForm):
    class Meta:
        model = Team
        fields = ("name", "desc", "creators", "universes", "cv_id", "gcd_id", "image")
        widgets = {
            "creators": CreatorsWidget(attrs={"class": "input"}),
            "universes": UniversesWidget(attrs={"class": "input"}),
            "image": ClearableFileInput(),
        }
