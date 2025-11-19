from autocomplete import widgets
from django.forms import ClearableFileInput, DateInput, ModelForm

from comicsdb.autocomplete import CreatorAutocomplete
from comicsdb.models import Creator

CreatorsWidget = widgets.AutocompleteWidget(
    ac_class=CreatorAutocomplete,
    attrs={"class": "input"},
    options={"multiselect": True},
)


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
            "alias": "Separate multiple aliases by a comma",
        }
