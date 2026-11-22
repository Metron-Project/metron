from django.core.cache import cache
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from api.cache import LIST_CACHE_TTL, ModelLabel, list_cache_key
from api.v1_0.serializers import (
    PublisherListSerializer,
    PublisherReadSerializer,
    PublisherSerializer,
    SeriesListSerializer,
)
from api.v1_0.views.mixins import (
    CatalogViewSet,
    mark_cache_status,
)
from api.v1_0.views.series import series_issue_count
from comicsdb.filters.publisher import PublisherFilter
from comicsdb.models import Publisher


class PublisherViewSet(CatalogViewSet):
    """
    list:
    Returns a list of all publishers.

    retrieve:
    Returns the information of an individual publisher.

    create:
    Add a new publisher.

    update:
    Update a publisher's information.
    """

    queryset = Publisher.objects.all()
    serializer_class = PublisherSerializer
    serializer_classes = {
        "list": PublisherListSerializer,
        "series_list": SeriesListSerializer,
        "retrieve": PublisherReadSerializer,
    }
    filterset_class = PublisherFilter
    parser_classes = (MultiPartParser, FormParser)
    cache_model_label = ModelLabel.PUBLISHER

    @extend_schema(responses={200: SeriesListSerializer(many=True)}, filters=False)
    @action(detail=True)
    def series_list(self, request, pk=None):
        """
        Returns a list of series for a publisher.
        """
        # get_object() (existence + permission check) first, same as any
        # other detail-scoped action -- a cache hit must not bypass either
        # of those, and must not keep serving a 200 once the publisher
        # itself has been deleted.
        publisher = self.get_object()

        # series_list's payload depends on the Series/Issue graph, not on
        # Publisher.modified (adding a series, or issues under one, doesn't
        # touch the publisher row) -- so this uses the version-counter list
        # scheme, scoped to this publisher, rather than a parent-modified
        # detail key.
        key = list_cache_key(
            ModelLabel.SERIES,
            ModelLabel.ISSUE,
            request=request,
            scope=f"publisher:{pk}:series_list",
        )
        cached = cache.get(key)
        if cached is not None:
            return mark_cache_status(Response(cached), hit=True)

        queryset = publisher.series.select_related("series_type", "publisher").annotate(
            num_issues=series_issue_count
        )
        page = self.paginate_queryset(queryset)
        if page is None:
            raise Http404
        serializer = SeriesListSerializer(page, many=True, context={"request": request})
        response = self.get_paginated_response(serializer.data)
        cache.set(key, response.data, LIST_CACHE_TTL)
        return mark_cache_status(response, hit=False)
