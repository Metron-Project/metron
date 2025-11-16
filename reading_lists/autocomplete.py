"""Autocomplete views for reading lists app."""

from autocomplete import ModelAutocomplete, register

from comicsdb.models.issue import Issue


class IssueAutocomplete(ModelAutocomplete):
    """Autocomplete for searching issues."""

    model = Issue
    search_attrs = ["series__name", "number", "name"]

    @classmethod
    def get_queryset(cls):
        """Return issues with series info for display."""
        queryset = super().get_queryset()
        return queryset.select_related("series", "series__series_type")

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


# Register the autocomplete
register(IssueAutocomplete)
