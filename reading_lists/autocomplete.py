"""Autocomplete views for reading_lists app."""

from autocomplete import ModelAutocomplete, register
from django.db.models import Q

from reading_lists.models import ReadingList


class ReadingListAutocomplete(ModelAutocomplete):
    """Autocomplete for searching reading lists."""

    model = ReadingList
    search_attrs = ["name"]

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter reading lists using unaccent search for accent-insensitive matching."""
        queryset = cls.get_queryset()
        return queryset.filter(Q(name__unaccent__icontains=search))

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


register(ReadingListAutocomplete)
