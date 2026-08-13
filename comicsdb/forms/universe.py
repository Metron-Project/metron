from django.forms import ClearableFileInput, ModelForm
from django.utils.translation import gettext_lazy as _

from comicsdb.autocomplete import UniverseAutocomplete
from comicsdb.forms.widgets import SafeAutocompleteWidget
from comicsdb.models import Universe

UniversesWidget = SafeAutocompleteWidget(
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
            "name": _(
                "Do not use a hyphen to separate text in this field. For example, "
                "<i>'Earth 2'</i> should <b>not</b> be <i>'Earth-2'</i>."
            ),
            "designation": _(
                "Do not use a hyphen to separate text in this field. For example, "
                "<i>'Earth 2'</i> should <b>not</b> be <i>'Earth-2'</i>."
            ),
        }
