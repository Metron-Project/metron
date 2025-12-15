import operator
from functools import reduce

import django_filters as df
from django.db.models import Q
from django_filters import rest_framework as filters

from comicsdb.models import Series


class SeriesNameFilter(filters.CharFilter):
    """Filter for series names with multi-word search support."""

    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(operator.and_, (Q(name__unaccent__icontains=q) for q in query_list))
            )
        return super().filter(qs, value)


class SeriesFilter(filters.FilterSet):
    name = SeriesNameFilter()
    publisher_id = filters.filters.NumberFilter(field_name="publisher__id", lookup_expr="exact")
    publisher_name = filters.CharFilter(field_name="publisher__name", lookup_expr="icontains")
    imprint_name = filters.CharFilter(field_name="imprint__name", lookup_expr="icontains")
    series_type_id = filters.filters.NumberFilter(field_name="series_type__id", lookup_expr="exact")
    series_type = filters.CharFilter(field_name="series_type__name", lookup_expr="icontains")
    status = filters.ChoiceFilter(choices=Series.Status)
    modified_gt = filters.DateTimeFilter(
        label="Greater than Modified DateTime", field_name="modified", lookup_expr="gt"
    )
    cv_id = filters.filters.NumberFilter(
        label="Comic Vine ID", field_name="cv_id", lookup_expr="exact"
    )
    missing_cv_id = filters.filters.BooleanFilter(field_name="cv_id", lookup_expr="isnull")
    gcd_id = filters.filters.NumberFilter(
        label="Grand Comics Database ID", field_name="gcd_id", lookup_expr="exact"
    )
    missing_gcd_id = filters.filters.BooleanFilter(field_name="gcd_id", lookup_expr="isnull")

    class Meta:
        model = Series
        fields = ["volume", "year_began", "year_end"]


class SeriesViewFilter(df.FilterSet):
    """Filter for series list views with search capabilities."""

    # Quick search for series names
    q = SeriesNameFilter(label="Quick Search")

    # Series name with multi-word support
    name = SeriesNameFilter(label="Series Name")

    # Series type filter
    series_type = df.NumberFilter(
        label="Series Type", field_name="series_type__id", lookup_expr="exact"
    )

    # Publisher/Imprint filters
    publisher_name = df.CharFilter(
        label="Publisher Name", field_name="publisher__name", lookup_expr="icontains"
    )
    publisher_id = df.NumberFilter(
        label="Publisher ID", field_name="publisher__id", lookup_expr="exact"
    )
    imprint_name = df.CharFilter(
        label="Imprint Name", field_name="imprint__name", lookup_expr="icontains"
    )
    imprint_id = df.NumberFilter(label="Imprint ID", field_name="imprint__id", lookup_expr="exact")

    # Year filters
    year_began = df.NumberFilter(label="Year Began")
    year_began_gte = df.NumberFilter(
        label="Year Began (>=)", field_name="year_began", lookup_expr="gte"
    )
    year_began_lte = df.NumberFilter(
        label="Year Began (<=)", field_name="year_began", lookup_expr="lte"
    )
    year_end = df.NumberFilter(label="Year Ended")

    # Status filter
    status = df.ChoiceFilter(label="Status", choices=Series.Status)

    # Volume filter
    volume = df.NumberFilter(label="Volume")

    class Meta:
        model = Series
        fields = [
            "q",
            "name",
            "series_type",
            "publisher_name",
            "publisher_id",
            "imprint_name",
            "imprint_id",
            "year_began",
            "year_began_gte",
            "year_began_lte",
            "year_end",
            "status",
            "volume",
        ]
