from django.db.models import Count
from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1_0.serializers.pull_list import (
    PullListIssueSerializer,
    PullListReadSerializer,
    PullListSeriesSerializer,
)
from api.v1_0.views.mixins import ConditionalRetrieveModelMixin
from comicsdb.models import Issue, Series
from pull_list.models import PullList, PullListSeries


class PullListViewSet(
    ConditionalRetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            PullList.objects.filter(user=self.request.user)
            .annotate(series_count=Count("series", distinct=True))
            .order_by("user")
        )

    def get_serializer_class(self):
        if self.action == "series":
            return PullListSeriesSerializer
        if self.action == "issues":
            return PullListIssueSerializer
        return PullListReadSerializer

    @extend_schema(responses=PullListSeriesSerializer(many=True))
    @action(detail=False, methods=["get"])
    def series(self, request):
        """Returns the authenticated user's pull list series."""
        pull_list, _ = PullList.objects.get_or_create(user=request.user)
        queryset = pull_list.pull_list_series.select_related(
            "series__series_type", "series__publisher"
        ).order_by("series__sort_name")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PullListSeriesSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404

    @extend_schema(
        request=None,
        responses={201: PullListSeriesSerializer, 200: PullListSeriesSerializer},
        parameters=[OpenApiParameter(name="series_id", type=int, location="query", required=True)],
    )
    @action(detail=False, methods=["post"], url_path="series/add")
    def add_series(self, request):
        """Add a series to the authenticated user's pull list."""
        series_id = request.data.get("series_id")
        if not series_id:
            return Response(
                {"detail": "series_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )
        try:
            series = Series.objects.get(pk=series_id)
        except Series.DoesNotExist:
            return Response(
                {"detail": f"Series with id {series_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        pull_list, _ = PullList.objects.get_or_create(user=request.user)
        pls, created = PullListSeries.objects.get_or_create(pull_list=pull_list, series=series)
        serializer = PullListSeriesSerializer(pls, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        responses=PullListIssueSerializer(many=True),
        parameters=[
            OpenApiParameter(
                name="store_date_after",
                type=str,
                location="query",
                description="Return issues with a store date on or after this date (YYYY-MM-DD).",
            ),
            OpenApiParameter(
                name="store_date_before",
                type=str,
                location="query",
                description="Return issues with a store date on or before this date (YYYY-MM-DD).",
            ),
        ],
    )
    @action(detail=False, methods=["get"])
    def issues(self, request):
        """Return issues for series on the authenticated user's pull list.

        Optionally filter by store date using store_date_after and store_date_before.
        """
        pull_list, _ = PullList.objects.get_or_create(user=request.user)
        series_ids = PullListSeries.objects.filter(pull_list=pull_list).values_list(
            "series_id", flat=True
        )
        queryset = (
            Issue.objects.filter(series_id__in=series_ids)
            .select_related("series__series_type", "series__publisher")
            .order_by("store_date", "series__sort_name", "number")
        )
        after = request.query_params.get("store_date_after")
        before = request.query_params.get("store_date_before")
        if after:
            queryset = queryset.filter(store_date__gte=after)
        if before:
            queryset = queryset.filter(store_date__lte=before)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PullListIssueSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404

    @extend_schema(
        responses={204: None, 404: None},
        parameters=[OpenApiParameter(name="series_pk", type=int, location="path", required=True)],
    )
    @action(
        detail=False,
        methods=["delete"],
        url_path=r"series/(?P<series_pk>[^/.]+)/remove",
    )
    def remove_series(self, request, series_pk=None):
        """Remove a series from the authenticated user's pull list."""
        pull_list, _ = PullList.objects.get_or_create(user=request.user)
        deleted, _ = PullListSeries.objects.filter(
            pull_list=pull_list, series_id=series_pk
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {"detail": "Series not found in pull list."}, status=status.HTTP_404_NOT_FOUND
        )
