from django.db.models import Count, OuterRef, Subquery
from django.db.models.functions import Coalesce
from rest_framework import mixins, viewsets

from api.cache import ModelLabel
from api.v1_0.serializers import (
    IssueListSerializer,
    SeriesListSerializer,
    SeriesReadSerializer,
    SeriesSerializer,
    SeriesTypeSerializer,
)
from api.v1_0.views.mixins import (
    CachedListModelMixin,
    ConditionalRetrieveModelMixin,
    IssueListMixin,
    UserTrackingMixin,
)
from comicsdb.filters.name import NameFilter
from comicsdb.filters.series import SeriesFilter
from comicsdb.models import Issue, Series
from comicsdb.models.series import SeriesType

# Correlated per-series issue count. Unlike Count("issues") -- which joins and
# GROUPs BY every issue row before sorting and paginating -- Postgres only
# evaluates this for the rows actually returned, and the pagination COUNT(*)
# drops it entirely. Coalesce because a series with no issues yields no row.
series_issue_count = Coalesce(
    Subquery(
        Issue.objects.filter(series=OuterRef("pk"))
        .values("series")
        .annotate(count=Count("pk"))
        .values("count")
    ),
    0,
)


class SeriesViewSet(
    UserTrackingMixin,
    IssueListMixin,
    mixins.CreateModelMixin,
    ConditionalRetrieveModelMixin,
    CachedListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Returns a list of all the comic series.

    retrieve:
    Returns the information of an individual comic series.

    create:
    Add a new Series.

    update:
    Update a Series information.
    """

    queryset = Series.objects.select_related("series_type", "publisher")
    filterset_class = SeriesFilter
    cache_model_label = ModelLabel.SERIES
    # Series list embeds num_issues, which changes on every Issue write.
    cache_dependent_labels = (ModelLabel.ISSUE,)
    # Series retrieve embeds its Publisher/Imprint name, which don't cascade
    # a `modified` bump onto this Series when renamed.
    cache_detail_dependent_labels = (ModelLabel.PUBLISHER_NAME, ModelLabel.IMPRINT_NAME)

    def get_modified_queryset(self):
        # get_queryset() adds select_related joins and a num_issues
        # subquery for list/retrieve. This lookup only needs the row's own
        # pk/modified.
        return Series.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        match self.action:
            case "list":
                queryset = queryset.annotate(num_issues=series_issue_count)
            case "retrieve":
                queryset = (
                    queryset.select_related("imprint")
                    .prefetch_related("genres", "associated")
                    .annotate(num_issues=series_issue_count)
                )
        return queryset

    def get_serializer_class(self):
        match self.action:
            case "list":
                return SeriesListSerializer
            case "issue_list":
                return IssueListSerializer
            case "retrieve":
                return SeriesReadSerializer
            case _:
                return SeriesSerializer

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        kwargs["context"] = self.get_serializer_context()

        if (
            self.action != "partial_update"
            and "data" in kwargs
            and not kwargs["data"].get("imprint")
        ):
            data = kwargs["data"].copy()
            data["imprint"] = None
            kwargs["data"] = data
        return serializer_class(*args, **kwargs)

    def get_issue_queryset(self, obj):
        return obj.issues.select_related("series", "series__series_type").order_by(
            "cover_date", "series", "number"
        )


class SeriesTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
    Returns a list of the Series Types available.
    """

    queryset = SeriesType.objects.all()
    serializer_class = SeriesTypeSerializer
    filterset_class = NameFilter
