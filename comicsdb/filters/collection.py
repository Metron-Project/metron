import operator
from functools import reduce

import django_filters as df
from django.db.models import Q
from django_filters import rest_framework as filters

from user_collection.models import GRADE_CHOICES, CollectionItem


class CollectionSeriesName(df.CharFilter):
    """Custom filter for multi-word series name search."""

    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(
                    operator.and_,
                    (Q(issue__series__name__unaccent__icontains=q) for q in query_list),
                )
            )
        return super().filter(qs, value)


class QuickSearchFilter(df.CharFilter):
    """Quick search across multiple fields: series name and notes."""

    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(
                    operator.and_,
                    (
                        Q(issue__series__name__unaccent__icontains=q) | Q(notes__icontains=q)
                        for q in query_list
                    ),
                )
            )
        return super().filter(qs, value)


class CollectionFilter(filters.FilterSet):
    book_format = filters.ChoiceFilter(choices=CollectionItem.BookFormat.choices)
    purchase_date = filters.DateFilter()
    purchase_date_gt = filters.DateFilter(field_name="purchase_date", lookup_expr="gt")
    purchase_date_lt = filters.DateFilter(field_name="purchase_date", lookup_expr="lt")
    purchase_date_gte = filters.DateFilter(field_name="purchase_date", lookup_expr="gte")
    purchase_date_lte = filters.DateFilter(field_name="purchase_date", lookup_expr="lte")
    purchase_store = filters.CharFilter(lookup_expr="icontains")
    storage_location = filters.CharFilter(lookup_expr="icontains")
    issue__series = filters.NumberFilter(field_name="issue__series__id", lookup_expr="exact")
    is_read = filters.BooleanFilter()
    date_read = filters.DateFilter()
    date_read_gt = filters.DateFilter(field_name="date_read", lookup_expr="gt")
    date_read_lt = filters.DateFilter(field_name="date_read", lookup_expr="lt")
    date_read_gte = filters.DateFilter(field_name="date_read", lookup_expr="gte")
    date_read_lte = filters.DateFilter(field_name="date_read", lookup_expr="lte")
    grade = filters.ChoiceFilter(choices=GRADE_CHOICES)
    grading_company = filters.ChoiceFilter(choices=CollectionItem.GradingCompany.choices)
    rating = filters.NumberFilter()
    modified_gt = filters.DateTimeFilter(
        label="Greater than Modified DateTime", field_name="modified", lookup_expr="gt"
    )

    class Meta:
        model = CollectionItem
        fields = [
            "book_format",
            "purchase_date",
            "purchase_date_gt",
            "purchase_date_lt",
            "purchase_date_gte",
            "purchase_date_lte",
            "purchase_store",
            "storage_location",
            "issue__series",
            "is_read",
            "date_read",
            "date_read_gt",
            "date_read_lt",
            "date_read_gte",
            "date_read_lte",
            "grade",
            "grading_company",
            "rating",
            "modified_gt",
        ]


class CollectionViewFilter(df.FilterSet):
    """Filter for collection list views with search capabilities."""

    # Quick search across multiple fields
    q = QuickSearchFilter(label="Quick Search")

    # Series filters
    series_name = CollectionSeriesName(
        label="Series Name", field_name="issue__series__name", lookup_expr="icontains"
    )
    series_type = df.NumberFilter(
        label="Series Type", field_name="issue__series__series_type__id", lookup_expr="exact"
    )

    # Issue filters
    issue_number = df.CharFilter(
        label="Issue Number", field_name="issue__number", lookup_expr="iexact"
    )

    # Publisher/Imprint filters
    publisher_name = df.CharFilter(
        label="Publisher Name", field_name="issue__series__publisher__name", lookup_expr="icontains"
    )
    publisher_id = df.NumberFilter(
        label="Publisher ID", field_name="issue__series__publisher__id", lookup_expr="exact"
    )
    imprint_name = df.CharFilter(
        label="Imprint Name", field_name="issue__series__imprint__name", lookup_expr="icontains"
    )
    imprint_id = df.NumberFilter(
        label="Imprint ID", field_name="issue__series__imprint__id", lookup_expr="exact"
    )

    # Collection metadata filters
    book_format = df.ChoiceFilter(label="Format", choices=CollectionItem.BookFormat.choices)
    is_read = df.BooleanFilter(label="Read Status")
    storage_location = df.CharFilter(label="Storage Location", lookup_expr="icontains")
    purchase_store = df.CharFilter(label="Purchase Store", lookup_expr="icontains")

    # Grading filters
    grade = df.ChoiceFilter(label="Grade", choices=GRADE_CHOICES)
    grading_company = df.ChoiceFilter(
        label="Grading Company", choices=CollectionItem.GradingCompany.choices
    )

    # Rating filter
    rating = df.NumberFilter(label="Rating")

    class Meta:
        model = CollectionItem
        fields = [
            "q",
            "series_name",
            "series_type",
            "issue_number",
            "publisher_name",
            "publisher_id",
            "imprint_name",
            "imprint_id",
            "book_format",
            "is_read",
            "storage_location",
            "purchase_store",
            "grade",
            "grading_company",
            "rating",
        ]
