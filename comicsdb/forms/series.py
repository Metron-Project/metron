from autocomplete import widgets
from django.forms import ModelChoiceField, ModelForm, ValidationError

from comicsdb.autocomplete import ImprintAutocomplete, PublisherAutocomplete, SeriesAutocomplete
from comicsdb.models import Imprint, Publisher, Series

# Series_Type objects id's
HC = 8
OMNI = 15
TPB = 10


SeriesWidget = widgets.AutocompleteWidget(
    ac_class=SeriesAutocomplete,
    attrs={"class": "input"},
)

MultiSeriesWidget = widgets.AutocompleteWidget(
    ac_class=SeriesAutocomplete,
    attrs={"class": "input"},
    options={"multiselect": True},
)


class SeriesForm(ModelForm):
    publisher = ModelChoiceField(
        queryset=Publisher.objects.all(),
        label="Publisher",
        widget=widgets.AutocompleteWidget(ac_class=PublisherAutocomplete),
    )
    imprint = ModelChoiceField(
        queryset=Imprint.objects.all(),
        label="Imprint",
        widget=widgets.AutocompleteWidget(ac_class=ImprintAutocomplete),
        required=False,
    )

    class Meta:
        model = Series
        fields = [
            "name",
            "sort_name",
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
            "volume": "This is <strong>not</strong> the year the series began. "
            "If you have a question, contact the site administrator.",
            "sort_name": """Most of the time it will be the same as the series name,
            but if the title starts with an article like 'The' it might be remove so
            that it is listed with like named series.""",
            "year_end": "Leave blank if a One-Shot, Annual, or Ongoing Series.",
            "associated": (
                "Associate the series with another series. For example, "
                "an annual with it's primary series."
            ),
            "genres": "Hold down “Control”, or “Command” on a Mac, to select more than one.",
            "collection": (
                "Whether a series has a collection title. "
                "Normally this only applies to Trade Paperbacks. "
                "For example, the 2015 Deathstroke Trade Paperback which has a collection "
                "title of 'Gods of War'."
            ),
        }
        labels = {"associated": "Associated Series", "collection": "Allow collection title?"}

        field_order = [
            "name",
            "sort_name",
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
                msg = (
                    "Adding a Comic Vine ID  is not allowed for Trade Paperbacks, "
                    "due to the consolidation work being done there."
                )
                raise ValidationError(msg)
        return cvid

    def clean_associated(self):
        assoc = self.cleaned_data["associated"]
        if assoc:
            series_type = self.cleaned_data.get("series_type")
            if series_type is None:
                return assoc
            # If adding an associated series and self.series_type is a TPB, OMNI, or HC
            # raise a validation error.
            if series_type.id in [HC, OMNI, TPB]:
                raise ValidationError("Collections are not allowed to have an associated series.")
        return assoc
