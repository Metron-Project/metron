import copy

from django.db.models import Model


class ModelCleanMixin:
    """
    Run the model's `clean()` when validating a serializer, since DRF doesn't call it.

    The request's values are applied to a copy of the instance being updated (or a new
    instance on create), so a partial update is checked against the stored values for any
    fields it leaves out. A Django `ValidationError` raised from `validate()` is converted
    by DRF into a serializer error, keeping its field keys and error codes.
    """

    def build_instance(self, attrs) -> Model:
        """Return an unsaved model instance with the validated values in `attrs` applied."""
        model = self.Meta.model
        instance = copy.copy(self.instance) if self.instance is not None else model()
        for name, value in attrs.items():
            field = model._meta.get_field(name)
            # Many-to-many values can't be assigned to an instance, and clean() doesn't use them.
            if field.concrete and not field.many_to_many:
                setattr(instance, name, value)
        return instance

    def validate(self, attrs):
        self.build_instance(attrs).clean()
        return attrs
