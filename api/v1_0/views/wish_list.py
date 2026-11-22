from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from djmoney.money import Money
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1_0.serializers.wish_list import (
    AcquireWishListItemSerializer,
    WishListAddItemSerializer,
    WishListItemListSerializer,
    WishListItemReadSerializer,
    WishListSerializer,
)
from api.v1_0.views.mixins import ConditionalRetrieveModelMixin
from comicsdb.models import Issue
from user_collection.models import CollectionItem
from wish_list.models import WishList, WishListItem


class WishListViewSet(
    ConditionalRetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            WishList.objects.filter(user=self.request.user)
            .annotate(item_count=Count("wish_list_items", distinct=True))
            .order_by("user")
        )

    def get_serializer_class(self):
        if self.action == "items":
            return WishListItemListSerializer
        return WishListSerializer

    @extend_schema(responses=WishListItemListSerializer(many=True))
    @action(detail=False, methods=["get"])
    def items(self, request):
        """Returns paginated wish list items for the authenticated user."""
        wish_list, _ = WishList.objects.get_or_create(user=request.user)
        queryset = wish_list.wish_list_items.select_related(
            "issue__series__series_type", "issue__series__publisher"
        ).order_by("priority", "issue__series__sort_name")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = WishListItemListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404

    @extend_schema(
        request=WishListAddItemSerializer,
        responses={201: WishListItemReadSerializer, 200: WishListItemReadSerializer},
    )
    @action(detail=False, methods=["post"], url_path="items/add")
    def add_item(self, request):
        """Add an issue to the authenticated user's wish list."""
        serializer = WishListAddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        issue = Issue.objects.get(pk=data["issue_id"])
        wish_list, _ = WishList.objects.get_or_create(user=request.user)
        max_price = data.get("max_price")
        max_price_currency = data.get("max_price_currency", "USD")
        item, created = WishListItem.objects.get_or_create(
            wish_list=wish_list,
            issue=issue,
            defaults={
                "priority": data.get("priority", 3),
                "notes": data.get("notes", ""),
                "desired_grade": data.get("desired_grade"),
                "max_price": Money(max_price, max_price_currency) if max_price else None,
            },
        )
        response_serializer = WishListItemReadSerializer(item, context={"request": request})
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        request=AcquireWishListItemSerializer,
        responses={200: None},
        parameters=[OpenApiParameter(name="item_pk", type=int, location="path", required=True)],
    )
    @action(
        detail=False,
        methods=["post"],
        url_path=r"items/(?P<item_pk>[^/.]+)/acquire",
    )
    def acquire_item(self, request, item_pk=None):
        """Mark a wish list item as acquired and create a collection item."""
        wish_list, _ = WishList.objects.get_or_create(user=request.user)
        item = get_object_or_404(WishListItem, pk=item_pk, wish_list=wish_list)
        serializer = AcquireWishListItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        purchase_price = data.get("purchase_price")
        purchase_price_currency = data.get("purchase_price_currency", "USD")
        collection_item, created = CollectionItem.objects.get_or_create(
            user=request.user,
            issue=item.issue,
            defaults={
                "purchase_date": data.get("purchase_date"),
                "purchase_price": Money(purchase_price, purchase_price_currency)
                if purchase_price
                else None,
                "purchase_store": data.get("purchase_store", ""),
                "notes": data.get("notes", ""),
                "grade": item.desired_grade,
            },
        )
        item.status = WishListItem.Status.ACQUIRED
        item.save(update_fields=["status", "modified"])
        return Response(
            {
                "wish_list_item_id": item.pk,
                "collection_item_id": collection_item.pk,
                "created": created,
                "status": item.get_status_display(),
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        responses={204: None, 404: None},
        parameters=[OpenApiParameter(name="item_pk", type=int, location="path", required=True)],
    )
    @action(
        detail=False,
        methods=["delete"],
        url_path=r"items/(?P<item_pk>[^/.]+)/remove",
    )
    def remove_item(self, request, item_pk=None):
        """Remove an item from the authenticated user's wish list."""
        wish_list, _ = WishList.objects.get_or_create(user=request.user)
        item = get_object_or_404(WishListItem, pk=item_pk, wish_list=wish_list)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
