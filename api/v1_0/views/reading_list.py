from django.db.models import Avg, Count, Q
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from api.v1_0.serializers import (
    ReadingListItemSerializer,
    ReadingListListSerializer,
    ReadingListReadSerializer,
)
from api.v1_0.views.mixins import ActionSerializerMixin, ConditionalRetrieveModelMixin
from comicsdb.filters.reading_list import ReadingListFilter
from reading_lists.models import ReadingList
from users.models import CustomUser


class ReadingListItemsPagination(PageNumberPagination):
    """Custom pagination for reading list items with 50 items per page."""

    page_size = 50


class ReadingListViewSet(
    ActionSerializerMixin,
    ConditionalRetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Returns a list of reading lists based on user permissions.
    Requires authentication.
    - Authenticated users: Public lists + own lists
    - Admin users: Public lists + own lists + Metron's lists

    retrieve:
    Returns the information of an individual reading list.
    Requires authentication.
    """

    queryset = ReadingList.objects.all()
    filterset_class = ReadingListFilter
    pagination_class = ReadingListItemsPagination
    serializer_class = ReadingListReadSerializer
    serializer_classes = {
        "list": ReadingListListSerializer,
        "items": ReadingListItemSerializer,
    }

    def get_queryset(self):
        """Filter reading lists based on user permissions and visibility rules."""
        queryset = (
            ReadingList.objects.select_related("user", "previous", "next")
            .annotate(
                average_rating=Avg("ratings__rating"),
                rating_count=Count("ratings", distinct=True),
            )
            .order_by("name", "attribution_source", "user")
        )

        # Unauthenticated users - only public lists
        if not self.request.user.is_authenticated:
            return queryset.filter(is_private=False)

        # Admin users - public lists + own lists + Metron's lists
        if self.request.user.is_staff:
            try:
                metron_user = CustomUser.objects.get(username="Metron")
                return queryset.filter(
                    Q(is_private=False) | Q(user=self.request.user) | Q(user=metron_user)
                ).distinct()
            except CustomUser.DoesNotExist:
                pass

        # Authenticated users - public lists + own lists
        return queryset.filter(Q(is_private=False) | Q(user=self.request.user)).distinct()

    @extend_schema(
        responses={200: ReadingListItemSerializer(many=True)},
        filters=False,
    )
    @action(detail=True)
    def items(self, request, pk=None):
        """Returns a paginated list of items for this reading list."""
        reading_list = self.get_object()
        queryset = reading_list.reading_list_items.select_related(
            "issue__series", "issue__series__series_type"
        ).order_by("order")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = ReadingListItemSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404
