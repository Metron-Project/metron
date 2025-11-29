from django_filters import rest_framework as filters

from reading_lists.models import ReadingList


class ReadingListFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="unaccent__icontains")
    user = filters.NumberFilter(field_name="user__id", lookup_expr="exact")
    username = filters.CharFilter(field_name="user__username", lookup_expr="icontains")
    attribution_source = filters.ChoiceFilter(choices=ReadingList.AttributionSource.choices)
    is_private = filters.BooleanFilter()
    modified_gt = filters.DateTimeFilter(
        label="Greater than Modified DateTime", field_name="modified", lookup_expr="gt"
    )

    class Meta:
        model = ReadingList
        fields = ["name", "user", "username", "attribution_source", "is_private", "modified_gt"]
