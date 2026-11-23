from django import forms
from djmoney.forms.widgets import MoneyWidget
from heggra import UploadWidget

# Largest image the upload widgets accept, in bytes. nginx's client_max_body_size (20M)
# stays a hard cap above it. heggra signs this limit into each upload's token, so changing it
# turns away uploads made before the deploy: their forms report the file as no longer available.
MAX_IMAGE_SIZE = 5 * 1024 * 1024


class BulmaMoneyWidget(MoneyWidget):
    """
    Custom MoneyWidget with Bulma CSS styling.

    MoneyWidget is a MultiWidget that renders two fields:
    - Amount field (NumberInput)
    - Currency field (Select)

    This widget applies Bulma 'input' and 'select' classes to both sub-widgets.
    """

    def __init__(self, attrs=None, choices=None):
        # Apply Bulma classes to the amount input
        amount_attrs = attrs.copy() if attrs else {}
        if "class" in amount_attrs:
            amount_attrs["class"] += " input"
        else:
            amount_attrs["class"] = "input"

        # Apply Bulma classes to the currency select (if needed)
        currency_attrs = {}
        if "class" in currency_attrs:
            currency_attrs["class"] += " select"
        else:
            currency_attrs["class"] = "select"

        super().__init__(
            amount_widget=forms.NumberInput(attrs=amount_attrs),
            currency_widget=forms.Select(attrs=currency_attrs, choices=choices)
            if choices
            else None,
        )

    def decompress(self, value):
        """Override to ensure proper value handling"""
        if value:
            return [
                value.amount,
                value.currency.code if hasattr(value, "currency") else value.currency,
            ]
        return [None, "USD"]


class ImageUploadWidget(UploadWidget):
    """heggra upload widget for images, limited to MAX_IMAGE_SIZE."""

    def __init__(self, **kwargs):
        kwargs.setdefault("image", True)
        kwargs.setdefault("max_size", MAX_IMAGE_SIZE)
        super().__init__(**kwargs)
