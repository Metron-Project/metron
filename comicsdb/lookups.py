"""Izaya lookups for comicsdb app."""

import operator
import re
from functools import reduce

from django.db.models import Case, Q, QuerySet, Value, When
from izaya import ModelLookup, register

from comicsdb.models import Arc, Character, Creator, Publisher, Series, Team, Universe
from comicsdb.models.credits import Role
from comicsdb.models.imprint import Imprint
from comicsdb.models.issue import Issue


class PublisherLabelMixin:
    """Add the publisher name to a lookup's labels, for models with a ``publisher`` FK."""

    def get_base_queryset(self) -> QuerySet:
        return super().get_base_queryset().select_related("publisher")

    def label(self, record) -> str:
        return f"{record} · {record.publisher.name}"


@register
class ArcLookup(ModelLookup):
    """Lookup for searching story arcs."""

    model = Arc
    search_fields = ["name__unaccent__icontains"]
    rank_fields = ["name__unaccent"]


@register
class CharacterLookup(ModelLookup):
    """Lookup for searching characters.

    Note: alias uses regular icontains as it's an ArrayField.
    """

    model = Character
    search_fields = ["name__unaccent__icontains", "alias__icontains"]
    rank_fields = ["name__unaccent"]


@register
class CreatorLookup(ModelLookup):
    """Lookup for searching creators.

    Note: alias uses regular icontains as it's an ArrayField.
    """

    model = Creator
    search_fields = ["name__unaccent__icontains", "alias__icontains"]
    rank_fields = ["name__unaccent"]

    def clean_query(self, query: str) -> str:
        """Keep one leading space, which editors type to search by surname (e.g. " Cameron")."""
        text = query.strip()
        return f" {text}" if text and query[0].isspace() else text

    def search(self, query, request):
        """
        Search creators, treating a leading space as a search for a later name.

        " Cameron" only matches names with "Cameron" after a space, so "Don Cameron" matches but
        "Cameron Stewart" doesn't. Names ending with the search text come first.
        """
        if not query.startswith(" "):
            return super().search(query, request)

        queryset = (
            self.get_queryset(request)
            .filter(Q(name__unaccent__icontains=query) | Q(alias__icontains=query))
            .alias(
                surname_rank=Case(
                    When(name__unaccent__iendswith=query, then=Value(0)), default=Value(1)
                )
            )
            .order_by("surname_rank", *self.model._meta.ordering)
        )
        return self.rank(queryset, query.strip())


@register
class RoleLookup(ModelLookup):
    """Lookup for searching creator roles."""

    model = Role
    search_fields = ["name__icontains"]


@register
class PublisherLookup(ModelLookup):
    """Lookup for searching publishers."""

    model = Publisher
    search_fields = ["name__unaccent__icontains"]
    rank_fields = ["name__unaccent"]


@register
class SeriesLookup(PublisherLabelMixin, ModelLookup):
    """Lookup for searching series.

    Note: alt_names uses the `joined` transform so the search can hit the trigram index on
    ArrayField(alt_names) instead of a seq scan.
    """

    model = Series
    search_fields = ["name__unaccent__icontains", "alt_names__joined__icontains"]
    rank_fields = ["name__unaccent"]

    def label(self, record: Series) -> str:
        """Return a label for the series, including the volume number and publisher name."""
        return f"{record} · v{record.volume} · {record.publisher.name}"


@register
class TeamLookup(ModelLookup):
    """Lookup for searching teams."""

    model = Team
    search_fields = ["name__unaccent__icontains"]
    rank_fields = ["name__unaccent"]


@register
class UniverseLookup(PublisherLabelMixin, ModelLookup):
    """Lookup for searching universes."""

    model = Universe
    search_fields = ["name__unaccent__icontains", "designation__unaccent__icontains"]
    rank_fields = ["name__unaccent"]


@register
class ImprintLookup(PublisherLabelMixin, ModelLookup):
    """Lookup for searching imprints."""

    model = Imprint
    search_fields = ["name__unaccent__icontains"]
    rank_fields = ["name__unaccent"]


@register
class IssueLookup(ModelLookup):
    """Lookup for searching issues."""

    model = Issue
    search_fields = ["series__name__icontains", "number__icontains", "alt_number__icontains"]

    def get_base_queryset(self) -> QuerySet:
        return super().get_base_queryset().select_related("series", "series__series_type")

    def search(self, query, request):
        """
        Filter issues with enhanced search logic.

        If the search contains '#', split it:
        - Text before '#' filters series name (unaccent__icontains for accent-insensitive)
        - Text after '#' filters issue number or alt_number (iexact)

        Otherwise, search series name, number, and alt_number with icontains.
        """
        if "#" not in query:
            return super().search(query, request)

        queryset = self.get_queryset(request)
        series_part, number_part = (part.strip() for part in query.split("#", 1))
        conditions = []

        # Add series name filter if there's text before '#'
        # Use unaccent for accent-insensitive series name matching
        # Split into words so order doesn't matter
        # (e.g., "Spider Amazing" matches "Amazing Spider-Man")
        # Also extract year if present in parentheses (e.g., "Speed Racer (2025)")
        if series_part:
            # Check for year in parentheses at the end
            year_match = re.search(r"\((\d{4})\)\s*$", series_part)
            if year_match:
                conditions.append(Q(series__year_began=int(year_match.group(1))))
                # Remove the year portion from series_part
                series_part = series_part[: year_match.start()].strip()

            # All series name words must match (if any remain after removing year)
            conditions.extend(
                Q(series__name__unaccent__icontains=word) for word in series_part.split()
            )

        # Add number filter if there's text after '#'
        # Search both number and alt_number fields
        if number_part:
            conditions.append(Q(number__iexact=number_part) | Q(alt_number__iexact=number_part))

        # If both parts are empty (just "#"), return empty queryset
        if not conditions:
            return queryset.none()
        return queryset.filter(reduce(operator.and_, conditions))
