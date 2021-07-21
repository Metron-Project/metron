from comicsdb.models import Series
from django.forms import ModelForm, Select, Textarea, TextInput


class SeriesForm(ModelForm):
    class Meta:
        model = Series
        exclude = ("edited_by", "slug")
        widgets = {
            "name": TextInput(attrs={"class": "input"}),
            "sort_name": TextInput(attrs={"class": "input"}),
            "volume": TextInput(attrs={"class": "input"}),
            "year_began": TextInput(attrs={"class": "input"}),
            "year_end": TextInput(attrs={"class": "input"}),
            "series_type": Select(),
            "publisher": Select(),
            "short_desc": TextInput(attrs={"class": "input"}),
            "desc": Textarea(attrs={"class": "textarea"}),
        }
