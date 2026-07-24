import operator
from functools import reduce

import django_filters as df
from django.db.models import Q

from comicsdb.models import Issue


class IssueSeriesName(df.rest_framework.CharFilter):
    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(operator.and_, (Q(series__name__unaccent__icontains=q) for q in query_list))
            )
        return super().filter(qs, value)


class IssueSeriesQuickSearch(df.rest_framework.CharFilter):
    """Multi-word search across the issue's series name and alternative names."""

    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(
                    operator.and_,
                    (
                        Q(series__name__unaccent__icontains=q)
                        | Q(series__alt_names__joined__icontains=q)
                        for q in query_list
                    ),
                )
            )
        return super().filter(qs, value)


class NumberInFilter(df.rest_framework.BaseInFilter, df.rest_framework.NumberFilter):
    pass


class IssueFilter(df.rest_framework.FilterSet):
    cover_year = df.rest_framework.NumberFilter(
        label="Cover Year", field_name="cover_date", lookup_expr="year"
    )
    cover_month = df.rest_framework.NumberFilter(
        label="Cover Month", field_name="cover_date", lookup_expr="month"
    )
    number = df.rest_framework.CharFilter(
        label="Issue Number", field_name="number", lookup_expr="iexact"
    )
    alt_number = df.rest_framework.CharFilter(
        label="Alternate Number", field_name="alt_number", lookup_expr="iexact"
    )
    publisher_name = df.rest_framework.CharFilter(
        label="Publisher Name", field_name="series__publisher__name", lookup_expr="icontains"
    )
    publisher_id = df.rest_framework.NumberFilter(
        label="Publisher Metron ID", field_name="series__publisher__id", lookup_expr="exact"
    )
    imprint_name = df.rest_framework.CharFilter(
        label="Imprint Name", field_name="series__imprint__name", lookup_expr="icontains"
    )
    imprint_id = df.rest_framework.NumberFilter(
        label="Imprint Metron ID", field_name="series__imprint__id", lookup_expr="exact"
    )
    series_name = IssueSeriesName(
        label="Series Name", field_name="series__name", lookup_expr="icontains"
    )
    series_alt_names = df.rest_framework.CharFilter(
        label="Series Alternative Name",
        field_name="series__alt_names",
        lookup_expr="joined__icontains",
    )
    series_q = IssueSeriesQuickSearch(label="Quick search across series name and alternative names")
    series_id = df.rest_framework.NumberFilter(
        label="Series Metron ID", field_name="series__id", lookup_expr="exact"
    )
    series_volume = df.rest_framework.NumberFilter(
        label="Series Volume Number", field_name="series__volume", lookup_expr="exact"
    )
    store_date_range = df.rest_framework.DateFromToRangeFilter("store_date")
    foc_date_range = df.rest_framework.DateFromToRangeFilter("foc_date")
    series_year_began = df.rest_framework.NumberFilter(
        label="Series Beginning Year", field_name="series__year_began", lookup_expr="exact"
    )
    modified_gt = df.rest_framework.DateTimeFilter(
        label="Greater than Modified DateTime", field_name="modified", lookup_expr="gt"
    )
    rating = df.rest_framework.CharFilter(
        label="Rating", field_name="rating__name", lookup_expr="iexact"
    )
    sku = df.rest_framework.CharFilter(
        label="Distributor SKU", field_name="sku", lookup_expr="iexact"
    )
    upc = df.rest_framework.CharFilter(label="UPC Code", field_name="upc", lookup_expr="iexact")
    upc_starts_with = df.rest_framework.CharFilter(
        label="UPC Code starts with (e.g. the 12-digit UPC-A read by a mobile scanner "
        "that strips the 5-digit EAN supplemental)",
        field_name="upc",
        lookup_expr="startswith",
    )
    cv_id = df.rest_framework.NumberFilter(
        label="Comic Vine ID", field_name="cv_id", lookup_expr="exact"
    )
    missing_cv_id = df.rest_framework.BooleanFilter(field_name="cv_id", lookup_expr="isnull")
    gcd_id = df.rest_framework.NumberFilter(
        label="Grand Comics Database ID", field_name="gcd_id", lookup_expr="exact"
    )
    missing_gcd_id = df.rest_framework.BooleanFilter(field_name="gcd_id", lookup_expr="isnull")
    cover_hash = df.rest_framework.CharFilter(
        label="Cover Hash", field_name="cover_hash", lookup_expr="iexact"
    )
    creator_id = df.rest_framework.NumberFilter(
        label="Creator Metron ID", field_name="creators__id", lookup_expr="exact", distinct=True
    )
    character_id = df.rest_framework.NumberFilter(
        label="Character Metron ID", field_name="characters__id", lookup_expr="exact", distinct=True
    )
    team_id = df.rest_framework.NumberFilter(
        label="Team Metron ID", field_name="teams__id", lookup_expr="exact", distinct=True
    )
    universe_id = df.rest_framework.NumberFilter(
        label="Universe Metron ID", field_name="universes__id", lookup_expr="exact", distinct=True
    )
    role_id = NumberInFilter(
        label="Role Metron ID", field_name="credits__role__id", lookup_expr="in", distinct=True
    )

    class Meta:
        model = Issue
        fields = ["store_date", "foc_date"]


class IssueViewFilter(df.FilterSet):
    """Filter for issue list views with search capabilities."""

    # Quick search for series names
    q = IssueSeriesName(label="Quick Search")

    cover_year = df.NumberFilter(label="Cover Year", field_name="cover_date", lookup_expr="year")
    cover_month = df.NumberFilter(label="Cover Month", field_name="cover_date", lookup_expr="month")
    number = df.rest_framework.CharFilter(
        label="Issue Number", field_name="number", lookup_expr="iexact"
    )
    alt_number = df.rest_framework.CharFilter(
        label="Alternate Number", field_name="alt_number", lookup_expr="iexact"
    )
    publisher_name = df.CharFilter(
        label="Publisher Name", field_name="series__publisher__name", lookup_expr="icontains"
    )
    publisher_id = df.NumberFilter(
        label="Publisher Metron ID", field_name="series__publisher__id", lookup_expr="exact"
    )
    series_name = IssueSeriesName(label="Series Name")
    series_id = df.NumberFilter(
        label="Series Metron ID", field_name="series__id", lookup_expr="exact"
    )
    series_volume = df.NumberFilter(
        label="Series Volume Number", field_name="series__volume", lookup_expr="exact"
    )
    series_type = df.NumberFilter(
        label="Series Type", field_name="series__series_type__id", lookup_expr="exact"
    )
    store_date = df.DateFromToRangeFilter("store_date")
    foc_date = df.DateFromToRangeFilter("foc_date")
    series_year_began = df.NumberFilter(
        label="Series Beginning Year", field_name="series__year_began", lookup_expr="exact"
    )
    sku = df.CharFilter(label="Distributor SKU", field_name="sku", lookup_expr="iexact")
    upc = df.CharFilter(label="UPC Code", field_name="upc", lookup_expr="iexact")
    cv_id = df.rest_framework.NumberFilter(
        label="Comic Vine ID", field_name="cv_id", lookup_expr="exact"
    )
    gcd_id = df.rest_framework.NumberFilter(
        label="Grand Comics Database ID", field_name="gcd_id", lookup_expr="exact"
    )

    class Meta:
        model = Issue
        fields = ["q"]
