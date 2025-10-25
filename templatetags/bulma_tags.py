from django import forms, template

register = template.Library()


@register.filter
def add_field_class(field, css_class):
    """adds css class to a field"""
    if len(field.errors) > 0 and "is-danger" not in css_class:
        # automatically add .is-danger to fields with invalid values
        css_class += " is-danger"

    if isinstance(field.field.widget, forms.SplitDateTimeWidget | forms.MultiWidget):
        # Handle SplitDateTimeWidget and MultiWidget (e.g., MoneyWidget)
        for subfield in field.field.widget.widgets:
            if subfield.attrs.get("class"):
                subfield.attrs["class"] += f" {css_class}"
            else:
                subfield.attrs["class"] = css_class
        return field

    if field.field.widget.attrs.get("class"):
        field.field.widget.attrs["class"] += f" {css_class}"
    else:
        field.field.widget.attrs["class"] = css_class

    return field


@register.filter
def is_field_type(field, field_type):  # NOQA: PLR0911
    """checks field type"""
    match field_type:
        case "file":
            return isinstance(field.field.widget, forms.FileInput)
        case "radio":
            return isinstance(field.field.widget, forms.RadioSelect)
        case "checkbox":
            return isinstance(field.field.widget, forms.CheckboxInput)
        case "split_dt":
            return isinstance(field.field.widget, forms.SplitDateTimeWidget)
        case "input":
            return isinstance(
                field.field.widget,
                forms.TextInput
                | forms.NumberInput
                | forms.EmailInput
                | forms.PasswordInput
                | forms.URLInput
                | forms.SplitDateTimeWidget,
            )
        case "textarea":
            return isinstance(field.field.widget, forms.Textarea)
        case "select":
            return isinstance(field.field.widget, forms.Select)
        case "any_datetime":
            return isinstance(
                field.field.widget,
                forms.DateInput | forms.TimeInput | forms.DateTimeInput | forms.SplitDateTimeWidget,
            )  # there is also forms.SplitHiddenDateTimeWidget, but we'll skip it
        case _:
            raise ValueError(f"Unsupported field_type on |is_field_type:'{field_type}'")


@register.filter
def is_multiple(field):
    """checks multiple field"""
    return isinstance(field.field.widget, forms.CheckboxSelectMultiple | forms.SelectMultiple)


@register.filter
def bulma_message_tag(tag):
    """
    messages use type "error", while bulma use class "danger"
    """
    return {"error": "danger"}.get(tag, tag)


@register.filter
def set_input_type(field, field_type=None):
    """
    changes the type by the widget, where django puts text-input by default instead
    of time/date/... but you can also pass your own field type if you want
    """
    if field_type:
        pass
    elif isinstance(field.field.widget, forms.DateInput):
        field_type = "date"
    elif isinstance(field.field.widget, forms.TimeInput):
        field_type = "time"
    elif isinstance(field.field.widget, forms.SplitDateTimeWidget):
        for subfield in field.field.widget.widgets:
            if isinstance(subfield, forms.DateInput):
                subfield.input_type = "date"
            elif isinstance(subfield, forms.TimeInput):
                subfield.input_type = "time"
    elif isinstance(field.field.widget, forms.DateTimeInput):
        # field_type = 'datetime-local'  # can't work with passing/returning ISO format
        # field_type = 'datetime'  # is deprecated, doesn't work in many browsers
        # use widget=forms.SplitDateTimeWidget() instead
        pass

    if field_type:
        field.field.widget.input_type = field_type

    return field
