from django.forms import ClearableFileInput, ModelForm
from django.utils.translation import gettext_lazy as _
from izaya import LookupWidget

from comicsdb.lookups import UniverseLookup
from comicsdb.models import Universe

UniversesWidget = LookupWidget(UniverseLookup, multiple=True)


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
