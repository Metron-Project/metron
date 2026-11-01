from django.forms import ClearableFileInput, DateInput, ModelForm
from django.utils.translation import gettext_lazy as _
from izaya import LookupWidget

from comicsdb.lookups import CreatorLookup
from comicsdb.models import Creator

CreatorsWidget = LookupWidget(CreatorLookup, multiple=True)


class CreatorForm(ModelForm):
    class Meta:
        model = Creator
        fields = (
            "name",
            "desc",
            "alias",
            "birth",
            "death",
            "cv_id",
            "gcd_id",
            "image",
        )
        widgets = {
            "birth": DateInput(attrs={"type": "date", "data-bulma-calendar": "on"}),
            "death": DateInput(attrs={"type": "date", "data-bulma-calendar": "on"}),
            "image": ClearableFileInput(),
        }
        help_texts = {
            "alias": _("Separate multiple aliases by a comma"),
        }
