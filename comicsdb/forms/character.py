from django.forms import ClearableFileInput, ModelForm
from django.utils.translation import gettext_lazy as _

from comicsdb.forms.creator import CreatorsWidget
from comicsdb.forms.team import TeamsWidget
from comicsdb.forms.universe import UniversesWidget
from comicsdb.models import Character


class CharacterForm(ModelForm):
    class Meta:
        model = Character
        fields = (
            "name",
            "desc",
            "alias",
            "creators",
            "teams",
            "universes",
            "cv_id",
            "gcd_id",
            "image",
        )
        widgets = {
            "creators": CreatorsWidget,
            "teams": TeamsWidget,
            "universes": UniversesWidget,
            "image": ClearableFileInput(),
        }
        help_texts = {
            "alias": _("Separate multiple aliases by a comma"),
        }
