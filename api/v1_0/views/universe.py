from rest_framework import mixins, viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from api.cache import ModelLabel
from api.v1_0.serializers import UniverseListSerializer, UniverseReadSerializer, UniverseSerializer
from api.v1_0.views.mixins import (
    CachedListModelMixin,
    ConditionalRetrieveModelMixin,
    UserTrackingMixin,
)
from comicsdb.filters.name import UniverseFilter
from comicsdb.models import Universe


class UniverseViewSet(
    UserTrackingMixin,
    mixins.CreateModelMixin,
    ConditionalRetrieveModelMixin,
    CachedListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Return a list of all the universes.

    retrieve:
    Returns the information of an individual universe.
    """

    queryset = Universe.objects.all()
    filterset_class = UniverseFilter
    parser_classes = (MultiPartParser, FormParser)
    cache_model_label = ModelLabel.UNIVERSE
    # Universe retrieve embeds its Publisher's name, which doesn't cascade a
    # `modified` bump onto this Universe when renamed.
    cache_detail_dependent_labels = (ModelLabel.PUBLISHER_NAME,)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.select_related("publisher")
        return queryset

    def get_serializer_class(self):
        match self.action:
            case "list":
                return UniverseListSerializer
            case "retrieve":
                return UniverseReadSerializer
            case _:
                return UniverseSerializer
