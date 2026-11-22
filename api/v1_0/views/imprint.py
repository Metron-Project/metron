from rest_framework.parsers import FormParser, MultiPartParser

from api.cache import ModelLabel
from api.v1_0.serializers import ImprintListSerializer, ImprintReadSerializer, ImprintSerializer
from api.v1_0.views.mixins import CatalogViewSet
from comicsdb.filters.name import ComicVineFilter
from comicsdb.models import Imprint


class ImprintViewSet(CatalogViewSet):
    """
    list:
    Returns a list of all imprints.

    retrieve:
    Returns the information of an individual imprint.

    create:
    Add a new imprint.

    update:
    Update an imprint's information.
    """

    queryset = Imprint.objects.all()
    serializer_class = ImprintSerializer
    serializer_classes = {
        "list": ImprintListSerializer,
        "retrieve": ImprintReadSerializer,
    }
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)
    cache_model_label = ModelLabel.IMPRINT
    # Imprint retrieve embeds its Publisher's name, which doesn't cascade a
    # `modified` bump onto this Imprint when renamed.
    cache_detail_dependent_labels = (ModelLabel.PUBLISHER_NAME,)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.select_related("publisher")
        return queryset
