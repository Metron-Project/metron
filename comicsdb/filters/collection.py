from django_filters import rest_framework as filters

from user_collection.models import CollectionItem


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
            "modified_gt",
        ]
