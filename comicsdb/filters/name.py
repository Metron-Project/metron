from django_filters import rest_framework as filters


class NameFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="unaccent__icontains")
    modified_gt = filters.DateTimeFilter(
        label="Greater than Modified DateTime", field_name="modified", lookup_expr="gt"
    )


class ComicVineFilter(NameFilter):
    cv_id = filters.NumberFilter(
        label="Comic Vine ID", field_name="cv_id", lookup_expr="exact"
    )
    gcd_id = filters.NumberFilter(
        label="Grand Comics Database ID", field_name="gcd_id", lookup_expr="exact"
    )


class UniverseFilter(NameFilter):
    designation = filters.CharFilter(lookup_expr="icontains")
