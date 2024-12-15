from django.forms import ClearableFileInput, ModelForm
from django_select2 import forms as s2forms

from comicsdb.models import Creator


class CreatorsWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
        "alias__icontains",
    ]


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
            "image": ClearableFileInput(),
        }
        help_texts = {
            "alias": "Separate multiple aliases by a comma",
        }
