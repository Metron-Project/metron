from autocomplete import widgets
from django.forms import ClearableFileInput, ModelForm

from comicsdb.autocomplete import UniverseAutocomplete
from comicsdb.models import Universe

UniversesWidget = widgets.AutocompleteWidget(
    ac_class=UniverseAutocomplete,
    attrs={"class": "input"},
    options={"multiselect": True},
)


class UniverseForm(ModelForm):
    class Meta:
        model = Universe
        fields = (
            "publisher",
            "name",
            "designation",
            "desc",
            "gcd_id",
            "image",
        )  # CV doesn't have universe resource
        widgets = {"image": ClearableFileInput()}
        help_texts = {
            "name": "Do not use a hyphen to separate text in this field. For example, "
            "<i>'Earth 2'</i> should <b>not</b> be <i>'Earth-2'</i>.",
            "designation": "Do not use a hyphen to separate text in this field. For example, "
            "<i>'Earth 2'</i> should <b>not</b> be <i>'Earth-2'</i>.",
        }
