from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from comicsdb.forms.creator import CreatorsWidget
from comicsdb.forms.team import TeamsWidget
from comicsdb.forms.universe import UniversesWidget
from comicsdb.forms.widgets import ImageUploadWidget
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
            "image": ImageUploadWidget(),
        }
        help_texts = {
            "alias": _("Separate multiple aliases by a comma"),
        }
