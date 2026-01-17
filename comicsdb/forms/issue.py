from autocomplete import widgets
from django.forms import (
    ClearableFileInput,
    DateInput,
    ModelChoiceField,
    ModelForm,
    ValidationError,
)
from isbnlib import canonical, is_isbn10, is_isbn13

from comicsdb.autocomplete import (
    ArcAutocomplete,
    CharacterAutocomplete,
    IssueAutocomplete,
    SeriesAutocomplete,
)
from comicsdb.forms.team import TeamsWidget
from comicsdb.forms.universe import UniversesWidget
from comicsdb.forms.widgets import BulmaMoneyWidget
from comicsdb.models import Issue, Rating, Series

MINIMUM_YEAR = 1900


ArcsWidget = widgets.AutocompleteWidget(
    ac_class=ArcAutocomplete,
    attrs={"class": "input"},
    options={"multiselect": True},
)

CharactersWidget = widgets.AutocompleteWidget(
    ac_class=CharacterAutocomplete,
    attrs={"class": "input"},
    options={"multiselect": True},
)

IssuesWidget = widgets.AutocompleteWidget(
    ac_class=IssueAutocomplete,
    attrs={"class": "input"},
    options={"multiselect": True},
)


class IssueForm(ModelForm):
    series = ModelChoiceField(
        queryset=Series.objects.all(),
        widget=widgets.AutocompleteWidget(
            ac_class=SeriesAutocomplete,
            attrs={
                "placeholder": "Autocomplete...",
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
            "cover_date": DateInput(attrs={"type": "date", "data-bulma-calendar": "on"}),
            "store_date": DateInput(attrs={"type": "date", "data-bulma-calendar": "on"}),
            "foc_date": DateInput(attrs={"type": "date", "data-bulma-calendar": "on"}),
            "price": BulmaMoneyWidget(),
            "arcs": ArcsWidget,
            "characters": CharactersWidget,
            "teams": TeamsWidget,
            "universes": UniversesWidget,
            "reprints": IssuesWidget,
            "image": ClearableFileInput(),
        }
        help_texts = {
            "alt_number": "Primarily used for legacy numbering for DC and Marvel comics.",
            "name": "Separate multiple story titles by a semicolon",
            "title": "Only used with Collected Editions like a Trade Paperback.",
            "price": "In United States currency",
            "reprints": "Search using 'Series Name (Year) #Number' format.",
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
                raise ValidationError("Collection Title field is not allowed for this series..")
        return collection_title

    def clean_arcs(self):
        arcs = self.cleaned_data["arcs"]
        if arcs:
            series: Series = self.cleaned_data["series"]
            if series.series_type.id in self.collections:
                raise ValidationError("Arcs cannot be added to Trade Paperbacks.")
        return arcs
