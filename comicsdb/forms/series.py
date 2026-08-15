from django.conf import settings
from django.contrib.postgres.forms import SimpleArrayField
from django.forms import CharField, ModelChoiceField, ModelForm, ValidationError
from django.utils.translation import gettext_lazy as _

from comicsdb.autocomplete import ImprintAutocomplete, PublisherAutocomplete, SeriesAutocomplete
from comicsdb.forms.widgets import SafeAutocompleteWidget
from comicsdb.models import Imprint, Publisher, Series

# Series_Type objects id's
HC = 8
OMNI = 15
TPB = 10


SeriesWidget = SafeAutocompleteWidget(
    ac_class=SeriesAutocomplete,
    attrs={"class": "input"},
)

MultiSeriesWidget = SafeAutocompleteWidget(
    ac_class=SeriesAutocomplete,
    attrs={"class": "input"},
    options={"multiselect": True},
)


class SeriesForm(ModelForm):
    publisher = ModelChoiceField(
        queryset=Publisher.objects.all(),
        label=_("Publisher"),
        widget=SafeAutocompleteWidget(ac_class=PublisherAutocomplete),
    )
    imprint = ModelChoiceField(
        queryset=Imprint.objects.all(),
        label=_("Imprint"),
        widget=SafeAutocompleteWidget(ac_class=ImprintAutocomplete),
        required=False,
    )
    alt_names = SimpleArrayField(
        CharField(max_length=255),
        delimiter=";",
        label=_("Alternative Names"),
        help_text=_("Separate multiple alternative names by a semicolon"),
        required=False,
    )

    class Meta:
        model = Series
        fields = [
            "name",
            "sort_name",
            "alt_names",
            "language",
            "volume",
            "year_began",
            "year_end",
            "series_type",
            "status",
            "collection",
            "publisher",
            "imprint",
            "cv_id",
            "gcd_id",
            "desc",
            "genres",
            "associated",
        ]
        widgets = {
            "associated": MultiSeriesWidget,
        }
        help_texts = {
            "volume": _(
                "This is <strong>not</strong> the year the series began. "
                "If you have a question, contact the site administrator."
            ),
            "sort_name": _(
                "Most of the time it will be the same as the series name, "
                "but if the title starts with an article like 'The' it might be remove so "
                "that it is listed with like named series."
            ),
            "year_end": _("Leave blank if a One-Shot, Annual, or Ongoing Series."),
            "associated": _(
                "Associate the series with another series. For example, "
                "an annual with it's primary series."
            ),
            "genres": _("Hold down “Control”, or “Command” on a Mac, to select more than one."),
            "collection": _(
                "Whether a series has a collection title. "
                "Normally this only applies to Trade Paperbacks. "
                "For example, the 2015 Deathstroke Trade Paperback which has a collection "
                "title of 'Gods of War'."
            ),
        }
        labels = {"associated": _("Associated Series"), "collection": _("Allow collection title?")}

        field_order = [
            "name",
            "sort_name",
            "alt_names",
            "language",
            "volume",
            "year_began",
            "year_end",
            "series_type",
            "status",
            "collection",
            "publisher",
            "imprint",
            "cv_id",
            "gcd_id",
            "desc",
            "genres",
            "associated",
        ]

    def clean_cv_id(self):
        cvid = self.cleaned_data["cv_id"]
        if cvid:
            try:
                series_type = self.cleaned_data["series_type"]
            except KeyError:
                return None
            # Don't allow cv_id information for Trade Paperbacks. Refer to:
            # https://github.com/Metron-Project/metron/issues/219
            if series_type.id == TPB:
                msg = _(
                    "Adding a Comic Vine ID  is not allowed for Trade Paperbacks, "
                    "due to the consolidation work being done there."
                )
                raise ValidationError(msg)
        return cvid

    def clean_language(self):
        language = self.cleaned_data.get("language")
        allowed = {code for code, _ in settings.LANGUAGES}
        if language and language not in allowed:
            raise ValidationError(
                _("Currently only English and Italian language Series are supported")
            )
        return language

    def clean_associated(self):
        assoc = self.cleaned_data["associated"]
        if assoc:
            series_type = self.cleaned_data.get("series_type")
            if series_type is None:
                return assoc
            # If adding an associated series and self.series_type is a TPB, OMNI, or HC
            # raise a validation error.
            if series_type.id in [HC, OMNI, TPB]:
                raise ValidationError(
                    _("Collections are not allowed to have an associated series.")
                )
        return assoc
