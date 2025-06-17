from dal import autocomplete
from django.forms import (
    ClearableFileInput,
    ModelChoiceField,
    ModelForm,
    ValidationError,
)
from django_select2 import forms as s2forms
from isbnlib import canonical, is_isbn10, is_isbn13

from comicsdb.forms.team import TeamsWidget
from comicsdb.forms.universe import UniversesWidget
from comicsdb.models import Issue, Rating, Series

MINIMUM_YEAR = 1900


class ArcsWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "name__icontains",
    ]


class CharactersWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = ["name__icontains", "alias__icontains"]


class IssuesWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = ["series__name__icontains", "number", "alt_number"]


class IssueForm(ModelForm):
    series = ModelChoiceField(
        queryset=Series.objects.all(),
        widget=autocomplete.ModelSelect2(
            url="issue:series-autocomplete",
            attrs={
                "data-placeholder": "Autocomplete...",
                "data-minimum-input-length": 3,
            },
        ),
    )

    rating = ModelChoiceField(queryset=Rating.objects.all(), empty_label=None)

    class Meta:
        model = Issue
        # exclude 'creators' field
        fields = (
            "series",
            "number",
            "alt_number",
            "title",
            "name",
            "cover_date",
            "store_date",
            "foc_date",
            "rating",
            "price",
            "sku",
            "isbn",
            "upc",
            "page",
            "cv_id",
            "gcd_id",
            "desc",
            "characters",
            "teams",
            "arcs",
            "universes",
            "reprints",
            "image",
        )
        widgets = {
            "arcs": ArcsWidget(attrs={"class": "input"}),
            "characters": CharactersWidget(attrs={"class": "input"}),
            "teams": TeamsWidget(attrs={"class": "input"}),
            "universes": UniversesWidget(attrs={"class": "input"}),
            "reprints": IssuesWidget(attrs={"class": "input"}),
            "image": ClearableFileInput(),
        }
        help_texts = {
            "alt_number": "Primarily used for legacy numbering for DC and Marvel comics.",
            "name": "Separate multiple story titles by a semicolon",
            "title": "Only used with Collected Editions like a Trade Paperback.",
            "price": "In United States currency",
            "reprints": (
                "Add any issues that are reprinted. Do not add a '#' "
                "in front of any issue number."
            ),
            "foc_date": "This date should be earlier than the store date",
        }
        labels = {
            "name": "Story Title",
            "title": "Collection Title",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, "instance", None)
        if instance and hasattr(instance, "series") and not instance.series.collection:
            self.fields["title"].disabled = True
        self.fields["name"].delimiter = ";"
        self.collections = [8, 10]

    def _validate_date(self, field: str):
        form_date = self.cleaned_data[field]
        if form_date is not None and form_date.year < MINIMUM_YEAR:
            raise ValidationError("Date has a non-valid year.")
        return form_date

    def clean_store_date(self):
        return self._validate_date("store_date")

    def clean_cover_date(self):
        return self._validate_date("cover_date")

    def clean_foc_date(self):
        return self._validate_date("foc_date")

    def clean_sku(self):
        sku = self.cleaned_data["sku"]
        if sku and not sku.isalnum():
            raise ValidationError("SKU must be alphanumeric. No spaces or hyphens allowed.")
        return sku

    def clean_isbn(self):
        isbn = ""
        if data := self.cleaned_data["isbn"]:
            isbn = canonical(data)
            if is_isbn10(isbn) or is_isbn13(isbn):
                return isbn
            raise ValidationError("ISBN is not a valid ISBN-10 or ISBN-13.")
        return isbn

    def clean_upc(self):
        upc = self.cleaned_data["upc"]
        if upc and not upc.isdigit():
            raise ValidationError("UPC must be numeric. No spaces or hyphens allowed.")
        return upc

    def clean_title(self):
        collection_title = self.cleaned_data["title"]
        if collection_title:
            series: Series = self.cleaned_data["series"]
            if not series.collection:
                raise ValidationError(
                    "Collection Title field is not allowed for this series.."
                )
        return collection_title

    def clean_arcs(self):
        arcs = self.cleaned_data["arcs"]
        if arcs:
            series: Series = self.cleaned_data["series"]
            if series.series_type.id in self.collections:
                raise ValidationError("Arcs cannot be added to Trade Paperbacks.")
        return arcs
