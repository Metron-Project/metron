from django.forms import ModelForm
from heggra import UploadWidget

from comicsdb.forms.publisher import PublisherWidget
from comicsdb.models import Imprint


class ImprintForm(ModelForm):
    class Meta:
        model = Imprint
        fields = ["name", "desc", "founded", "publisher", "cv_id", "gcd_id", "image"]
        widgets = {
            "image": UploadWidget(image=True),
            "publisher": PublisherWidget,
        }
        field_order = ["name", "desc", "founded", "publisher", "cv_id", "gcd_id", "image"]
