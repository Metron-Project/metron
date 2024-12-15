from django.forms import ClearableFileInput, ModelForm

from comicsdb.models import Arc


class ArcForm(ModelForm):
    class Meta:
        model = Arc
        fields = ("name", "desc", "cv_id", "gcd_id", "image")
        widgets = {
            "image": ClearableFileInput(),
        }
