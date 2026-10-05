"""Autocomplete views for reading_lists app."""

from autocomplete import ModelAutocomplete, register
from django.db.models import Q

from reading_lists.models import ReadingList


class ReadingListAutocomplete(ModelAutocomplete):
    """Autocomplete for searching reading lists.

    Only used to pick a list's previous/next entries, so results are limited to
    lists the requesting user can manage (matching ReadingListForm's choices).
    """

    model = ReadingList
    search_attrs = ["name"]

    @classmethod
    def get_queryset_for_context(cls, context):
        return cls.get_queryset().manageable_by(context.request.user)

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter reading lists using unaccent search for accent-insensitive matching."""
        queryset = cls.get_queryset_for_context(context)
        return queryset.filter(Q(name__unaccent__icontains=search))

    @classmethod
    def get_items_from_keys(cls, keys, context):
        # The widget passes no context when rendering a form's stored value server
        # side; those keys come from the form instance, not the client, and the
        # form's own queryset still validates any submitted value.
        if context is None:
            return super().get_items_from_keys(keys, context)
        queryset = cls.get_queryset_for_context(context).filter(id__in=keys)
        return [
            {"key": record.id, "label": cls.get_label_for_record(record)} for record in queryset
        ]

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


register(ReadingListAutocomplete)
