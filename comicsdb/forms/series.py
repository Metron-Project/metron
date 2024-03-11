from django.forms import ModelForm, ValidationError
from django_select2 import forms as s2forms

from comicsdb.models import Series

# Series_Type objects id's
TPB = 10
HC = 8


class SeriesWidget(s2forms.ModelSelect2Widget):
    search_fields = ["name__icontains"]


class MultiSeriesWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = ["name__icontains"]


class SeriesForm(ModelForm):
    class Meta:
        model = Series
        fields = [
            "name",
            "sort_name",
            "volume",
            "year_began",
            "year_end",
            "series_type",
            "collection",
            "publisher",
            "cv_id",
            "desc",
            "genres",
            "associated",
        ]
        widgets = {
            "associated": MultiSeriesWidget(attrs={"class": "input"}),
        }
        help_texts = {
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
            "collection",
            "publisher",
            "cv_id",
            "desc",
            "genres",
            "associated",
        ]

    def clean_cv_id(self) -> any:
        cvid = self.cleaned_data["cv_id"]
        if cvid:
            series_type = self.cleaned_data["series_type"]
            # Don't cv_id for Trade Paperbacks. Refer to:
            # https://github.com/bpepple/metron/issues/219
            if series_type.id == TPB:
                msg = (
                    "Adding a Comic Vine ID  is not allowed for Trade Paperbacks, "
                    "due to the consolidation work being done there."
                )
                raise ValidationError(msg)
        return cvid

    def clean_associated(self) -> any:
        assoc = self.cleaned_data["associated"]
        if assoc:
            series_type = self.cleaned_data["series_type"]
            # If adding an associated series and self.series_type is a TPB or HC
            # raise a validation error.
            if series_type.id in [HC, TPB]:
                raise ValidationError(
                    "Collections are not allowed to have an associated series."
                )
        return assoc
