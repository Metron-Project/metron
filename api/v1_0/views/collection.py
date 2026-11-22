from django.db import models
from django.db.models import Case, Count, F, IntegerField, Sum, When
from django.utils import timezone
from djmoney.money import Money
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1_0.serializers import (
    CollectionAddItemSerializer,
    CollectionListSerializer,
    CollectionRatingUpdateSerializer,
    CollectionReadSerializer,
    MissingIssueSerializer,
    MissingSeriesSerializer,
    ScrobbleRequestSerializer,
    ScrobbleResponseSerializer,
)
from api.v1_0.views.mixins import ActionSerializerMixin, ConditionalRetrieveModelMixin
from comicsdb.filters.collection import CollectionFilter
from comicsdb.models import Issue, Series
from user_collection.models import CollectionItem


class CollectionViewSet(
    ActionSerializerMixin,
    ConditionalRetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Returns authenticated user's collection items.
    Requires authentication.

    retrieve:
    Returns details of a specific collection item (must belong to authenticated user).
    Requires authentication.

    partial_update:
    Update the rating of a specific collection item (must belong to authenticated user).
    Read-tracking fields (is_read/date_read) are not editable here; use scrobble instead.
    Requires authentication.

    update:
    Update the rating of a specific collection item (must belong to authenticated user).
    Read-tracking fields (is_read/date_read) are not editable here; use scrobble instead.
    Requires authentication.

    destroy:
    Remove a specific collection item (must belong to authenticated user).
    Requires authentication.
    """

    permission_classes = [IsAuthenticated]
    filterset_class = CollectionFilter
    serializer_class = CollectionReadSerializer
    serializer_classes = {
        "list": CollectionListSerializer,
        "update": CollectionRatingUpdateSerializer,
        "partial_update": CollectionRatingUpdateSerializer,
    }

    def get_queryset(self):
        """Only return collection items belonging to the authenticated user."""
        return (
            CollectionItem.objects.filter(user=self.request.user)
            .select_related("issue__series__series_type", "issue__series__publisher")
            .prefetch_related("read_dates")
        )

    @extend_schema(
        request=CollectionAddItemSerializer,
        responses={201: CollectionReadSerializer, 200: CollectionReadSerializer},
        description="Add an issue to the authenticated user's collection.",
    )
    @action(detail=False, methods=["post"])
    def add(self, request):
        """Add an issue to the authenticated user's collection.

        If the issue is already in the collection, the existing item is
        returned unchanged.
        """
        serializer = CollectionAddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        issue = Issue.objects.get(pk=data["issue_id"])
        purchase_price = data.get("purchase_price")
        purchase_price_currency = data.get("purchase_price_currency", "USD")
        item, created = CollectionItem.objects.get_or_create(
            user=request.user,
            issue=issue,
            defaults={
                "quantity": data.get("quantity", 1),
                "book_format": data.get("book_format", CollectionItem.BookFormat.PRINT),
                "grade": data.get("grade"),
                "grading_company": data.get("grading_company", ""),
                "purchase_date": data.get("purchase_date"),
                "purchase_price": Money(purchase_price, purchase_price_currency)
                if purchase_price
                else None,
                "purchase_store": data.get("purchase_store", ""),
                "storage_location": data.get("storage_location", ""),
                "notes": data.get("notes", ""),
            },
        )
        response_serializer = CollectionReadSerializer(item, context={"request": request})
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        responses={
            200: {
                "type": "object",
                "properties": {
                    "total_items": {"type": "integer"},
                    "total_quantity": {"type": "integer"},
                    "total_value": {"type": "string"},
                    "read_count": {"type": "integer"},
                    "unread_count": {"type": "integer"},
                    "by_format": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "book_format": {"type": "string"},
                                "count": {"type": "integer"},
                            },
                        },
                    },
                },
            }
        },
        filters=False,
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Return statistics about the user's collection."""
        queryset = CollectionItem.objects.filter(user=self.request.user)
        stats = queryset.aggregate(
            total_items=Count("id"),
            total_quantity=Sum("quantity"),
            total_value=Sum("purchase_price"),
            read_count=Count(Case(When(is_read=True, then=1), output_field=IntegerField())),
            unread_count=Count(Case(When(is_read=False, then=1), output_field=IntegerField())),
        )
        format_counts = queryset.values("book_format").annotate(count=Count("id"))

        return Response(
            {
                "total_items": stats["total_items"] or 0,
                "total_quantity": stats["total_quantity"] or 0,
                "total_value": str(stats["total_value"]) if stats["total_value"] else "0.00",
                "read_count": stats["read_count"],
                "unread_count": stats["unread_count"],
                "by_format": format_counts,
            }
        )

    @extend_schema(responses={200: MissingSeriesSerializer(many=True)}, filters=False)
    @action(detail=False, methods=["get"])
    def missing_series(self, request):
        """Return series where the user has some issues but is missing others."""
        user = request.user

        # Annotate all series with total and owned issue counts
        # Then filter to only show series with missing issues
        queryset = (
            Series.objects.annotate(
                total_issues=Count("issues", distinct=True),
                owned_issues=Count(
                    "issues", filter=models.Q(issues__in_collections__user=user), distinct=True
                ),
            )
            .annotate(missing_count=F("total_issues") - F("owned_issues"))
            .filter(owned_issues__gt=0, missing_count__gt=0)
            .select_related("publisher", "series_type", "imprint")
            .order_by("-missing_count", "sort_name")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MissingSeriesSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = MissingSeriesSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        responses={200: MissingIssueSerializer(many=True)},
        parameters=[
            OpenApiParameter(
                name="series_id",
                type=int,
                location=OpenApiParameter.PATH,
                description="ID of the series to get missing issues for",
            )
        ],
        filters=False,
    )
    @action(detail=False, methods=["get"], url_path="missing_issues/(?P<series_id>[^/.]+)")
    def missing_issues(self, request, series_id=None):
        """Return specific missing issues for a series."""
        user = request.user

        # Get user's owned issue IDs for this series
        owned_issue_ids = CollectionItem.objects.filter(
            user=user, issue__series_id=series_id
        ).values_list("issue_id", flat=True)

        # Get all issues from series that user doesn't own
        queryset = (
            Issue.objects.filter(series_id=series_id)
            .exclude(id__in=owned_issue_ids)
            .select_related("series", "series__publisher", "series__series_type")
            .order_by("cover_date", "number")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MissingIssueSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)

        serializer = MissingIssueSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        request=ScrobbleRequestSerializer,
        responses={
            201: ScrobbleResponseSerializer,
            200: ScrobbleResponseSerializer,
            400: {"type": "object"},
            404: {"type": "object"},
        },
        description="Mark an issue as read (scrobble). Auto-creates collection item if needed.",
    )
    @action(detail=False, methods=["post"])
    def scrobble(self, request):
        """
        Mark an issue as read with optional rating and date_read.

        If the issue is not in the user's collection, it will be automatically
        added with quantity=1 and is_read=True.

        If the issue is already in the collection, the read status and date will
        be updated.

        Returns:
        - 201: Created new collection item
        - 200: Updated existing collection item
        - 400: Validation error
        - 404: Issue not found
        """

        serializer = ScrobbleRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        issue_id = serializer.validated_data["issue_id"]
        rating = serializer.validated_data.get("rating")
        date_read = serializer.validated_data.get("date_read")

        # Default date_read to now if not provided
        if date_read is None:
            date_read = timezone.now()

        try:
            issue = Issue.objects.get(pk=issue_id)
        except Issue.DoesNotExist:
            return Response(
                {"detail": f"Issue with id {issue_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get or create collection item
        collection_item, created = CollectionItem.objects.get_or_create(
            user=request.user,
            issue=issue,
            defaults={
                "quantity": 1,
                "book_format": CollectionItem.BookFormat.DIGITAL,
            },
        )

        # Add read date (this will also set is_read=True and date_read)
        collection_item.add_read_date(date_read)

        # Update rating if provided
        if rating is not None:
            collection_item.rating = rating
            collection_item.save(update_fields=["rating"])

        # Return appropriate status code and response
        response_serializer = ScrobbleResponseSerializer(
            collection_item, context={"request": request}
        )
        response_data = response_serializer.data
        response_data["created"] = created

        return Response(
            response_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
