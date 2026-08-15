from django.conf import settings
from django.contrib.postgres.forms import SimpleArrayField
from django.forms import CharField, ClearableFileInput, ModelForm, ValidationError
from django.utils.translation import gettext_lazy as _

from comicsdb.autocomplete import PublisherAutocomplete
from comicsdb.forms.widgets import SafeAutocompleteWidget
from comicsdb.models import Publisher

PublisherWidget = SafeAutocompleteWidget(
    ac_class=PublisherAutocomplete,
    attrs={"class": "input"},
)


class PublisherForm(ModelForm):
    alt_names = SimpleArrayField(
        CharField(max_length=255),
        delimiter=";",
        label=_("Alternative Names"),
        help_text=_("Separate multiple alternative names by a semicolon"),
        required=False,
    )

    class Meta:
        model = Publisher
        fields = ["name", "alt_names", "desc", "founded", "country", "cv_id", "gcd_id", "image"]
        widgets = {
            "image": ClearableFileInput(),
        }

    field_order = [
        "name",
        "alt_names",
        "desc",
        "founded",
        "country",
        "cv_id",
        "gcd_id",
        "image",
    ]

    def clean_country(self):
        country = self.cleaned_data["country"]
        if country and str(country) not in settings.COUNTRIES:
            raise ValidationError(_("Currently only US, UK, and Italian Publishers are supported"))
        return country
