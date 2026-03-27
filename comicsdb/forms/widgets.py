from autocomplete import widgets as ac_widgets
from django import forms
from djmoney.forms.widgets import MoneyWidget


class SafeAutocompleteWidget(ac_widgets.AutocompleteWidget):
    """AutocompleteWidget subclass that handles empty-string values gracefully.

    The upstream widget crashes when ``value`` is ``''`` because it passes
    ``['']`` to ``get_items_from_keys``, which in turn calls
    ``queryset.filter(id__in=[''])`` and raises a ValueError.  This subclass
    normalises empty strings (and empty lists) to ``None`` before delegating to
    the parent so the widget simply renders with no pre-selected item.
    """

    def get_context(self, name, value, attrs):
        if value in ("", []):
            value = None
        return super().get_context(name, value, attrs)


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
