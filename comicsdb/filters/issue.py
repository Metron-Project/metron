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
                reduce(
                    operator.and_, (Q(series__name__unaccent__icontains=q) for q in query_list)
                )
            )
        return super().filter(qs, value)


class IssueFilter(df.rest_framework.FilterSet):
    cover_year = df.rest_framework.NumberFilter(
        label="Cover Year", field_name="cover_date", lookup_expr="year"
    )
    cover_month = df.rest_framework.NumberFilter(
        label="Cover Month", field_name="cover_date", lookup_expr="month"
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
    series_id = df.rest_framework.NumberFilter(
        label="Series Metron ID", field_name="series__id", lookup_expr="exact"
    )
    series_volume = df.rest_framework.NumberFilter(
        label="Series Volume Number", field_name="series__volume", lookup_expr="exact"
    )
    store_date_range = df.rest_framework.DateFromToRangeFilter("store_date")
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
    upc = df.rest_framework.CharFilter(
        label="UPC Code", field_name="upc", lookup_expr="iexact"
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

    class Meta:
        model = Issue
        fields = ["number", "alt_number", "store_date"]


class IssueViewFilter(df.FilterSet):
    cover_year = df.NumberFilter(
        label="Cover Year", field_name="cover_date", lookup_expr="year"
    )
    cover_month = df.NumberFilter(
        label="Cover Month", field_name="cover_date", lookup_expr="month"
    )
    publisher_name = df.CharFilter(
        label="Publisher Name", field_name="series__publisher__name", lookup_expr="icontains"
    )
    publisher_id = df.NumberFilter(
        label="Publisher Metron ID", field_name="series__publisher__id", lookup_expr="exact"
    )
    series_name = IssueSeriesName(
        label="Series Name", field_name="series__name", lookup_expr="icontains"
    )
    series_id = df.NumberFilter(
        label="Series Metron ID", field_name="series__id", lookup_expr="exact"
    )
    series_volume = df.NumberFilter(
        label="Series Volume Number", field_name="series__volume", lookup_expr="exact"
    )
    series_type = df.NumberFilter(
        label="Series Type", field_name="series__series_type__id", lookup_expr="exact"
    )
    store_date_range = df.DateFromToRangeFilter("store_date")
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
        fields = ["number", "alt_number", "store_date"]
