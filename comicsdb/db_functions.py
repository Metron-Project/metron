"""Custom Postgres function wrappers for ORM expressions.

`array_to_string()` is marked STABLE (not IMMUTABLE) in Postgres, even for
plain text arrays, which means it can't be used in an index expression. We
wrap it in our own IMMUTABLE SQL function (created in migration 0055) so
ArrayField values can be joined into a searchable string that a GIN trigram
index can actually accelerate.
"""

from django.contrib.postgres.fields import ArrayField
from django.db.models import CharField, Func, Transform, Value


class ArrayToString(Func):
    """Joins an ArrayField's elements with a space, via the immutable wrapper."""

    function = "array_to_string_immutable"
    output_field = CharField()

    def __init__(self, expression, **extra):
        super().__init__(expression, Value(" "), **extra)


class ArrayJoinedTransform(Transform):
    """Registers `<arrayfield>__joined` so it can be chained like `__icontains`."""

    lookup_name = "joined"
    output_field = CharField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return f"array_to_string_immutable({lhs}, %s)", (*params, " ")


ArrayField.register_lookup(ArrayJoinedTransform)
