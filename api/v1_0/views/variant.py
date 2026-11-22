from rest_framework import mixins, viewsets

from api.v1_0.serializers import VariantSerializer
from comicsdb.models.variant import Variant


class VariantViewset(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    create:
    Add a new Variant Cover.

    update:
    Update a Variant Cover's information."""

    queryset = Variant.objects.all()
    serializer_class = VariantSerializer
