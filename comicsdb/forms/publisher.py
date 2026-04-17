from django.forms import ClearableFileInput, ModelForm, ValidationError

from comicsdb.autocomplete import PublisherAutocomplete
from comicsdb.forms.widgets import SafeAutocompleteWidget
from comicsdb.models import Publisher

PublisherWidget = SafeAutocompleteWidget(
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
        country = self.cleaned_data["country"]
        allowed = {"US", "GB"}
        if country and str(country) not in allowed:
            raise ValidationError("Currently only US and UK Publishers are supported")
        return country
