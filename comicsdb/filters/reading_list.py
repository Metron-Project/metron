import operator
from functools import reduce

import django_filters as df
from django.db.models import Q
from django_filters import rest_framework as filters

from reading_lists.models import ReadingList


class QuickSearchFilter(df.CharFilter):
    """Quick search by reading list name."""

    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(
                    operator.and_,
                    (Q(name__unaccent__icontains=q) for q in query_list),
                )
            )
        return super().filter(qs, value)


class ReadingListFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="unaccent__icontains")
    user = filters.NumberFilter(field_name="user__id", lookup_expr="exact")
    username = filters.CharFilter(field_name="user__username", lookup_expr="icontains")
    attribution_source = filters.ChoiceFilter(choices=ReadingList.AttributionSource.choices)
    list_type = filters.ChoiceFilter(choices=ReadingList.ListType.choices)
    is_private = filters.BooleanFilter()
    modified_gt = filters.DateTimeFilter(
        label="Greater than Modified DateTime", field_name="modified", lookup_expr="gt"
    )
    average_rating__gte = filters.NumberFilter(
        field_name="average_rating",
        lookup_expr="gte",
        label="Minimum Rating",
    )

    class Meta:
        model = ReadingList
        fields = [
            "name",
            "user",
            "username",
            "attribution_source",
            "list_type",
            "is_private",
            "modified_gt",
            "average_rating__gte",
        ]


class ReadingListViewFilter(df.FilterSet):
    """Filter for reading list views with search capabilities."""

    # Quick search across multiple fields
    q = QuickSearchFilter(label="Quick Search")

    # List name filter
    name = df.CharFilter(label="List Name", lookup_expr="unaccent__icontains")

    # User/Creator filter
    username = df.CharFilter(label="Creator", field_name="user__username", lookup_expr="icontains")

    # Attribution source filter
    attribution_source = df.ChoiceFilter(
        label="Attribution Source", choices=ReadingList.AttributionSource.choices
    )

    # List type filter
    list_type = df.ChoiceFilter(label="List Type", choices=ReadingList.ListType.choices)

    # Privacy filter
    is_private = df.BooleanFilter(label="Private")

    # Publisher filter — uses a subquery to avoid combining the deep JOIN chain
    # with the COUNT/AVG aggregations, which causes extreme slowness.
    publisher = df.CharFilter(
        label="Publisher",
        method="filter_by_publisher",
    )

    # Rating filter
    average_rating__gte = df.NumberFilter(
        field_name="average_rating",
        lookup_expr="gte",
        label="Minimum Rating",
    )

    def filter_by_publisher(self, queryset, name, value):
        matching_ids = (
            ReadingList.objects.filter(
                reading_list_items__issue__series__publisher__name__icontains=value
            )
            .values("id")
            .distinct()
        )
        return queryset.filter(id__in=matching_ids)

    class Meta:
        model = ReadingList
        fields = [
            "q",
            "name",
            "username",
            "publisher",
            "attribution_source",
            "list_type",
            "is_private",
            "average_rating__gte",
        ]
