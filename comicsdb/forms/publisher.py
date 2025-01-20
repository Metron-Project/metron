from django.forms import ClearableFileInput, ModelForm, ValidationError
from django_select2 import forms as s2forms

from comicsdb.models import Publisher


class PublisherWidget(s2forms.ModelSelect2Widget):
    search_fields = ["name__icontains"]


class PublisherForm(ModelForm):
    class Meta:
        model = Publisher
        fields = ["name", "desc", "founded", "country", "cv_id", "gcd_id", "image"]
        widgets = {
            "image": ClearableFileInput(),
        }

    field_order = ["name", "desc", "founded", "country", "cv_id", "gcd_id", "image"]

    def clean_country(self):
        # Only allow US publishers for now.
        country = self.cleaned_data["country"]
        if country and country != "US":
            raise ValidationError("Currently only US Publishers are supported")
        return country
