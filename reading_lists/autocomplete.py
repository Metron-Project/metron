"""Autocomplete views for reading lists app."""

import operator
from functools import reduce

from autocomplete import ModelAutocomplete, register
from django.db.models import Q

from comicsdb.models.issue import Issue


class IssueAutocomplete(ModelAutocomplete):
    """Autocomplete for searching issues."""

    model = Issue
    search_attrs = ["series__name", "number"]

    @classmethod
    def get_queryset(cls):
        """Return issues with series info for display."""
        queryset = super().get_queryset()
        return queryset.select_related("series", "series__series_type")

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """
        Filter issues with enhanced search logic.

        If the search contains '#', split it:
        - Text before '#' filters series name (icontains)
        - Text after '#' filters issue number (icontains)

        Otherwise, search both series name and number with icontains.
        """
        base_qs = cls.get_queryset()

        # Check if search contains '#' for smart parsing
        if "#" in search:
            parts = search.split("#", 1)  # Split only on first '#'
            series_part = parts[0].strip()
            number_part = parts[1].strip()

            conditions = []

            # Add series name filter if there's text before '#'
            if series_part:
                conditions.append(Q(series__name__icontains=series_part))

            # Add number filter if there's text after '#'
            if number_part:
                # If we have both series and number, combine with AND
                if conditions:
                    conditions.append(Q(number__icontains=number_part))
                else:
                    # If only number is provided (e.g., "#100")
                    conditions.append(Q(number__icontains=number_part))

            # Combine conditions with AND if both parts exist, otherwise use the single condition
            if len(conditions) > 1:
                queryset = base_qs.filter(reduce(operator.and_, conditions))
            elif conditions:
                queryset = base_qs.filter(conditions[0])
            else:
                # If both parts are empty (just "#"), return empty queryset
                queryset = base_qs.none()
        else:
            # Original behavior: search both fields with OR
            conditions = [Q(**{f"{attr}__icontains": search}) for attr in cls.get_search_attrs()]
            condition_filter = reduce(operator.or_, conditions)
            queryset = base_qs.filter(condition_filter)

        return queryset


# Register the autocomplete
register(IssueAutocomplete)
