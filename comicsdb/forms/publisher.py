from django.forms import ClearableFileInput, ModelForm
from django_select2 import forms as s2forms

from comicsdb.models import Publisher


class PublisherWidget(s2forms.ModelSelect2Widget):
    search_fields = ["name__icontains"]


class PublisherForm(ModelForm):
    class Meta:
        model = Publisher
        fields = ["name", "desc", "founded", "cv_id", "gcd_id", "image"]
        widgets = {
            "image": ClearableFileInput(),
        }

    field_order = ["name", "desc", "founded", "cv_id", "gcd_id", "image"]
