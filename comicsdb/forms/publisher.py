from autocomplete import widgets
from django.forms import ClearableFileInput, ModelForm, ValidationError

from comicsdb.autocomplete import PublisherAutocomplete
from comicsdb.models import Publisher

PublisherWidget = widgets.AutocompleteWidget(
    ac_class=PublisherAutocomplete,
    attrs={"class": "input"},
)


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
