from django.forms import ClearableFileInput, ModelForm, TextInput, inlineformset_factory

from comicsdb.forms.widgets import BulmaMoneyWidget
from comicsdb.models import Variant
from comicsdb.models.issue import Issue


class VariantForm(ModelForm):
    class Meta:
        model = Variant
        fields = ("image", "name", "price", "sku", "upc")
        widgets = {
            "name": TextInput(attrs={"class": "input"}),
            "price": BulmaMoneyWidget(),
            "sku": TextInput(attrs={"class": "input"}),
            "upc": TextInput(attrs={"class": "input"}),
            "image": ClearableFileInput(),
        }


VariantFormset = inlineformset_factory(Issue, Variant, form=VariantForm, extra=3, can_delete=True)
