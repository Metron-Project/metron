from django import forms

from django_nyt import models


class SettingsForm(forms.ModelForm):
    class Meta:
        model = models.Settings
        fields = (
            "interval",
            "is_default",
        )
