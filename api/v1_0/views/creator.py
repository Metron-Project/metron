from rest_framework import mixins, status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from api.cache import ModelLabel
from api.v1_0.serializers import (
    CreatorListSerializer,
    CreatorReadSerializer,
    CreatorSerializer,
    CreditSerializer,
    RoleSerializer,
)
from api.v1_0.views.mixins import (
    CatalogViewSet,
)
from comicsdb.filters.name import ComicVineFilter, NameFilter
from comicsdb.models import Creator, Credits, Role


class CreatorViewSet(CatalogViewSet):
    """
    list:
    Return a list of all the creators.

    retrieve:
    Returns the information of an individual creator.
    """

    queryset = Creator.objects.all()
    serializer_class = CreatorSerializer
    serializer_classes = {
        "list": CreatorListSerializer,
        "retrieve": CreatorReadSerializer,
    }
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)
    cache_model_label = ModelLabel.CREATOR


class CreditViewset(
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """
    create:
    Add a new Credit.

    update:
    Update a Credit's data."""

    queryset = Credits.objects.all()
    serializer_class = CreditSerializer

    def create(self, request, *args, **kwargs) -> Response:
        serializer: CreditSerializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class RoleViewset(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
    Returns a list of all the creator roles.
    """

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filterset_class = NameFilter
