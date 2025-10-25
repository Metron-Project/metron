from django import forms
from djmoney.forms.widgets import MoneyWidget


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
        return [None, None]
