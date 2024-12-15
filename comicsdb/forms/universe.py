from django.forms import ClearableFileInput, ModelForm
from django_select2 import forms as s2forms

from comicsdb.models import Universe


class UniversesWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = ["name__icontains", "designation__icontains"]


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
