import operator
from functools import reduce

from django.db.models import Q
from django_filters import rest_framework as filters

from comicsdb.filters.name import ComicVineFilter


class PublisherQuickSearchFilter(filters.CharFilter):
    """Multi-word search across a publisher's name and its alternative names."""

    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(
                    operator.and_,
                    (
                        Q(name__unaccent__icontains=q) | Q(alt_names__joined__icontains=q)
                        for q in query_list
                    ),
                )
            )
        return super().filter(qs, value)


class PublisherFilter(ComicVineFilter):
    alt_names = filters.CharFilter(field_name="alt_names", lookup_expr="joined__icontains")
    q = PublisherQuickSearchFilter(label="Quick search across name and alternative names")
