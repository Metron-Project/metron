from django.forms import ModelForm

from comicsdb.forms.publisher import PublisherWidget
from comicsdb.forms.widgets import ImageUploadWidget
from comicsdb.models import Imprint


class ImprintForm(ModelForm):
    class Meta:
        model = Imprint
        fields = ["name", "desc", "founded", "publisher", "cv_id", "gcd_id", "image"]
        widgets = {
            "image": ImageUploadWidget(),
            "publisher": PublisherWidget,
        }
        field_order = ["name", "desc", "founded", "publisher", "cv_id", "gcd_id", "image"]
