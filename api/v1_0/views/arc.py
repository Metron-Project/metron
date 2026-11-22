from rest_framework.parsers import FormParser, MultiPartParser

from api.cache import ModelLabel
from api.v1_0.serializers import (
    ArcListSerializer,
    ArcReadSerializer,
    ArcSerializer,
    IssueListSerializer,
)
from api.v1_0.views.mixins import CatalogViewSet, IssueListMixin
from comicsdb.filters.name import ComicVineFilter
from comicsdb.models import Arc


class ArcViewSet(IssueListMixin, CatalogViewSet):
    """
    list:
    Returns a list of all the story arcs.

    retrieve:
    Returns the information of an individual story arc.
    """

    queryset = Arc.objects.all()
    serializer_class = ArcSerializer
    serializer_classes = {
        "list": ArcListSerializer,
        "issue_list": IssueListSerializer,
        "retrieve": ArcReadSerializer,
    }
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)
    cache_model_label = ModelLabel.ARC
