"""Autocomplete views for comicsdb app."""

import operator
import re
from functools import reduce

from autocomplete import ModelAutocomplete, register
from django.db.models import Q

from comicsdb.models import Arc, Character, Creator, Publisher, Series, Team, Universe
from comicsdb.models.imprint import Imprint
from comicsdb.models.issue import Issue


class ArcAutocomplete(ModelAutocomplete):
    """Autocomplete for searching story arcs."""

    model = Arc
    search_attrs = ["name"]

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter arcs using unaccent search for accent-insensitive matching."""
        queryset = cls.get_queryset()
        conditions = [
            Q(**{f"{attr}__unaccent__icontains": search}) for attr in cls.get_search_attrs()
        ]
        condition_filter = reduce(operator.or_, conditions)
        return queryset.filter(condition_filter)

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


class CharacterAutocomplete(ModelAutocomplete):
    """Autocomplete for searching characters."""

    model = Character
    search_attrs = ["name", "alias"]

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """
        Filter characters using unaccent search on name field.

        This allows searching for characters without needing to match accents.
        For example, searching "Rene" will match "René".
        Note: alias field uses regular icontains as it's an ArrayField.
        """
        queryset = cls.get_queryset()
        # Use unaccent for name, regular icontains for alias (ArrayField)
        conditions = [
            Q(name__unaccent__icontains=search),
            Q(alias__icontains=search),
        ]
        condition_filter = reduce(operator.or_, conditions)
        return queryset.filter(condition_filter)

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


class CreatorAutocomplete(ModelAutocomplete):
    """Autocomplete for searching creators."""

    model = Creator
    search_attrs = ["name", "alias"]

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """
        Filter creators using unaccent search on name field.

        This allows searching for creators without needing to match accents.
        For example, searching "Pena" will match "Peña".
        Note: alias field uses regular icontains as it's an ArrayField.
        """
        queryset = cls.get_queryset()
        # Use unaccent for name, regular icontains for alias (ArrayField)
        conditions = [
            Q(name__unaccent__icontains=search),
            Q(alias__icontains=search),
        ]
        condition_filter = reduce(operator.or_, conditions)
        return queryset.filter(condition_filter)

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


class PublisherAutocomplete(ModelAutocomplete):
    """Autocomplete for searching publishers."""

    model = Publisher
    search_attrs = ["name"]

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter publishers using unaccent search for accent-insensitive matching."""
        queryset = cls.get_queryset()
        conditions = [
            Q(**{f"{attr}__unaccent__icontains": search}) for attr in cls.get_search_attrs()
        ]
        condition_filter = reduce(operator.or_, conditions)
        return queryset.filter(condition_filter)

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


class SeriesAutocomplete(ModelAutocomplete):
    """Autocomplete for searching series."""

    model = Series
    search_attrs = ["name"]

    @classmethod
    def get_queryset(cls):
        """Return series with related info for display."""
        queryset = super().get_queryset()
        return queryset.select_related("series_type")

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter series using unaccent search for accent-insensitive matching."""
        queryset = cls.get_queryset()
        conditions = [
            Q(**{f"{attr}__unaccent__icontains": search}) for attr in cls.get_search_attrs()
        ]
        condition_filter = reduce(operator.or_, conditions)
        return queryset.filter(condition_filter)

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


class TeamAutocomplete(ModelAutocomplete):
    """Autocomplete for searching teams."""

    model = Team
    search_attrs = ["name"]

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter teams using unaccent search for accent-insensitive matching."""
        queryset = cls.get_queryset()
        conditions = [
            Q(**{f"{attr}__unaccent__icontains": search}) for attr in cls.get_search_attrs()
        ]
        condition_filter = reduce(operator.or_, conditions)
        return queryset.filter(condition_filter)

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


class UniverseAutocomplete(ModelAutocomplete):
    """Autocomplete for searching universes."""

    model = Universe
    search_attrs = ["name", "designation"]

    @classmethod
    def get_queryset(cls):
        """Return universes with publisher info for display."""
        queryset = super().get_queryset()
        return queryset.select_related("publisher")

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter universes using unaccent search for accent-insensitive matching."""
        queryset = cls.get_queryset()
        conditions = [
            Q(**{f"{attr}__unaccent__icontains": search}) for attr in cls.get_search_attrs()
        ]
        condition_filter = reduce(operator.or_, conditions)
        return queryset.filter(condition_filter)

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


class ImprintAutocomplete(ModelAutocomplete):
    """Autocomplete for searching imprints."""

    model = Imprint
    search_attrs = ["name"]

    @classmethod
    def get_queryset(cls):
        """Return imprints with publisher info for display."""
        queryset = super().get_queryset()
        return queryset.select_related("publisher")

    @classmethod
    def get_query_filtered_queryset(cls, search, context):
        """Filter imprints using unaccent search for accent-insensitive matching."""
        queryset = cls.get_queryset()
        conditions = [
            Q(**{f"{attr}__unaccent__icontains": search}) for attr in cls.get_search_attrs()
        ]
        condition_filter = reduce(operator.or_, conditions)
        return queryset.filter(condition_filter)

    @classmethod
    def get_label_for_record(cls, record):
        """Format the display name for autocomplete results."""
        return str(record)


class IssueAutocomplete(ModelAutocomplete):
    """Autocomplete for searching issues."""

    model = Issue
    search_attrs = ["series__name", "number", "alt_number"]

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
        - Text before '#' filters series name (unaccent__icontains for accent-insensitive)
        - Text after '#' filters issue number or alt_number (icontains)

        Otherwise, search series name, number, and alt_number with icontains.
        """
        base_qs = cls.get_queryset()

        # Check if search contains '#' for smart parsing
        if "#" in search:
            parts = search.split("#", 1)  # Split only on first '#'
            series_part = parts[0].strip()
            number_part = parts[1].strip()

            conditions = []

            # Add series name filter if there's text before '#'
            # Use unaccent for accent-insensitive series name matching
            # Split into words so order doesn't matter (e.g., "Spider Amazing" matches "Amazing Spider-Man")
            # Also extract year if present in parentheses (e.g., "Speed Racer (2025)")
            if series_part:
                # Check for year in parentheses at the end
                year_match = re.search(r"\((\d{4})\)\s*$", series_part)
                if year_match:
                    year = int(year_match.group(1))
                    # Remove the year portion from series_part
                    series_part = series_part[: year_match.start()].strip()
                    conditions.append(Q(series__year_began=year))

                # Filter by series name words (if any remain after removing year)
                if series_part:
                    series_words = series_part.split()
                    series_conditions = [
                        Q(series__name__unaccent__icontains=word) for word in series_words
                    ]
                    # All words must match (AND logic)
                    conditions.append(reduce(operator.and_, series_conditions))

            # Add number filter if there's text after '#'
            # Search both number and alt_number fields
            if number_part:
                conditions.append(Q(number__iexact=number_part) | Q(alt_number__iexact=number_part))

            # Combine conditions with AND if both parts exist, otherwise use the single condition
            if len(conditions) > 1:
                queryset = base_qs.filter(reduce(operator.and_, conditions))
            elif conditions:
                queryset = base_qs.filter(conditions[0])
            else:
                # If both parts are empty (just "#"), return empty queryset
                queryset = base_qs.none()
        else:
            # Original behavior: search all fields with OR
            conditions = [Q(**{f"{attr}__icontains": search}) for attr in cls.get_search_attrs()]
            condition_filter = reduce(operator.or_, conditions)
            queryset = base_qs.filter(condition_filter)

        return queryset


# Register all autocomplete classes
register(ArcAutocomplete)
register(CharacterAutocomplete)
register(CreatorAutocomplete)
register(ImprintAutocomplete)
register(IssueAutocomplete)
register(PublisherAutocomplete)
register(SeriesAutocomplete)
register(TeamAutocomplete)
register(UniverseAutocomplete)
