from django_filters import rest_framework as filters

from comicsdb.filters.name import ComicVineFilter


class PublisherFilter(ComicVineFilter):
    alt_names = filters.CharFilter(field_name="alt_names", lookup_expr="joined__icontains")
