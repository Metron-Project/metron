from django.db import models
from django.db.models import Avg, Count, F, Prefetch, Q, Sum
from django.http import Http404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.v1_0.serializers import (
    ArcListSerializer,
    ArcSerializer,
    CharacterListSerializer,
    CharacterReadSerializer,
    CharacterSerializer,
    CollectionListSerializer,
    CollectionReadSerializer,
    CreatorListSerializer,
    CreatorSerializer,
    CreditSerializer,
    ImprintListSerializer,
    ImprintReadSerializer,
    ImprintSerializer,
    IssueListSerializer,
    IssueReadSerializer,
    IssueSerializer,
    MissingIssueSerializer,
    MissingSeriesSerializer,
    PublisherListSerializer,
    PublisherSerializer,
    ReadingListItemSerializer,
    ReadingListListSerializer,
    ReadingListReadSerializer,
    RoleSerializer,
    ScrobbleRequestSerializer,
    ScrobbleResponseSerializer,
    SeriesListSerializer,
    SeriesReadSerializer,
    SeriesSerializer,
    SeriesTypeSerializer,
    TeamListSerializer,
    TeamReadSerializer,
    TeamSerializer,
    UniverseListSerializer,
    UniverseReadSerializer,
    UniverseSerializer,
    VariantSerializer,
)
from comicsdb.filters.collection import CollectionFilter
from comicsdb.filters.issue import IssueFilter
from comicsdb.filters.name import ComicVineFilter, NameFilter, UniverseFilter
from comicsdb.filters.reading_list import ReadingListFilter
from comicsdb.filters.series import SeriesFilter
from comicsdb.models import (
    Arc,
    Character,
    Creator,
    Credits,
    Imprint,
    Issue,
    Publisher,
    Role,
    Series,
    Team,
    Universe,
)
from comicsdb.models.series import SeriesType
from comicsdb.models.variant import Variant
from reading_lists.models import ReadingList
from user_collection.models import CollectionItem
from users.models import CustomUser


class ReadingListItemsPagination(PageNumberPagination):
    """Custom pagination for reading list items with 50 items per page."""

    page_size = 50


class UserTrackingMixin:
    """Mixin to automatically track user edits in create and update operations."""

    def perform_create(self, serializer):
        serializer.save(edited_by=self.request.user, created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(edited_by=self.request.user)


class IssueListMixin:
    """Mixin to provide a standard issue_list action for related models."""

    def get_issue_queryset(self, obj):
        """Override to customize the issue queryset for a specific viewset."""
        return obj.issues.select_related("series", "series__series_type").order_by(
            "cover_date", "series", "number"
        )

    @extend_schema(responses={200: IssueListSerializer(many=True)})
    @action(detail=True)
    def issue_list(self, request, pk=None):
        """Returns a list of issues for this object."""
        obj = self.get_object()
        queryset = self.get_issue_queryset(obj)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = IssueListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404


class ArcViewSet(
    UserTrackingMixin,
    IssueListMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Returns a list of all the story arcs.

    retrieve:
    Returns the information of an individual story arc.
    """

    queryset = Arc.objects.all()
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        match self.action:
            case "list":
                return ArcListSerializer
            case "issue_list":
                return IssueListSerializer
            case _:
                return ArcSerializer


class CharacterViewSet(
    UserTrackingMixin,
    IssueListMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Return a list of all the characters.

    retrieve:
    Returns the information of an individual character.
    """

    queryset = Character.objects.all()
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("creators", "teams", "universes")
        return queryset

    def get_serializer_class(self):
        match self.action:
            case "list":
                return CharacterListSerializer
            case "issue_list":
                return IssueListSerializer
            case "retrieve":
                return CharacterReadSerializer
            case _:
                return CharacterSerializer


class CreatorViewSet(
    UserTrackingMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Return a list of all the creators.

    retrieve:
    Returns the information of an individual creator.
    """

    queryset = Creator.objects.all()
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        match self.action:
            case "list":
                return CreatorListSerializer
            case _:
                return CreatorSerializer


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


class ImprintViewSet(
    UserTrackingMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
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

    queryset = Imprint.objects.prefetch_related("series", "series__series_type")
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.select_related("publisher")
        return queryset

    def get_serializer_class(self):
        match self.action:
            case "list":
                return ImprintListSerializer
            case "retrieve":
                return ImprintReadSerializer
            case _:
                return ImprintSerializer


class IssueViewSet(
    UserTrackingMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Return a list of all the issues.

    retrieve:
    Returns the information of an individual issue.

    Note: cover_hash is a Perceptual hashing created with
    ImageHash. https://github.com/JohannesBuchner/imagehash
    """

    queryset = Issue.objects.select_related(
        "series",
        "series__series_type",
        "series__publisher",
        "series__imprint",
        "rating",
    ).prefetch_related(
        "series__genres",
        "arcs",
        "characters",
        "teams",
        "universes",
        "variants",
        Prefetch(
            "credits_set",
            queryset=Credits.objects.order_by("creator__name")
            .distinct("creator__name")
            .select_related("creator")
            .prefetch_related("role"),
        ),
        Prefetch(
            "reprints",
            queryset=Issue.objects.select_related("series", "series__series_type"),
        ),
    )
    filterset_class = IssueFilter
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        match self.action:
            case "list":
                return IssueListSerializer
            case "retrieve":
                return IssueReadSerializer
            case _:
                return IssueSerializer


class PublisherViewSet(
    UserTrackingMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Returns a list of all publishers.

    retrieve:
    Returns the information of an individual publisher.

    create:
    Add a new publisher.

    update:
    Update a publisher's information.
    """

    queryset = Publisher.objects.prefetch_related("series")
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)

    def get_serializer_class(self):
        match self.action:
            case "list":
                return PublisherListSerializer
            case "series_list":
                return SeriesListSerializer
            case _:
                return PublisherSerializer

    @extend_schema(responses={200: SeriesListSerializer(many=True)})
    @action(detail=True)
    def series_list(self, request, pk=None):
        """
        Returns a list of series for a publisher.
        """
        publisher = self.get_object()
        queryset = publisher.series.select_related("series_type").prefetch_related("issues")
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = SeriesListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404


class RoleViewset(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
    Returns a list of all the creator roles.
    """

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filterset_class = NameFilter


class SeriesViewSet(
    UserTrackingMixin,
    IssueListMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
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

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.select_related("imprint").prefetch_related("genres", "associated")
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

        if self.request.method in {"POST", "PUT", "PATCH"} and not self.request.data.get("imprint"):
            series_request_data = self.request.data.copy()
            series_request_data["imprint"] = None
            kwargs["data"] = series_request_data
        return serializer_class(*args, **kwargs)

    def get_issue_queryset(self, obj):
        """Series issues don't need extra optimization - already optimized at queryset level."""
        return obj.issues.all()


class SeriesTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
    Returns a list of the Series Types available.
    """

    queryset = SeriesType.objects.all()
    serializer_class = SeriesTypeSerializer
    filterset_class = NameFilter


class TeamViewSet(
    UserTrackingMixin,
    IssueListMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Return a list of all the teams.

    retrieve:
    Returns the information of an individual team.
    """

    queryset = Team.objects.all()
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("creators", "universes")
        return queryset

    def get_serializer_class(self):
        match self.action:
            case "list":
                return TeamListSerializer
            case "issue_list":
                return IssueListSerializer
            case "retrieve":
                return TeamReadSerializer
            case _:
                return TeamSerializer


class UniverseViewSet(
    UserTrackingMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
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


class ReadingListViewSet(
    mixins.RetrieveModelMixin,
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

    def get_queryset(self):
        """Filter reading lists based on user permissions and visibility rules."""
        queryset = (
            ReadingList.objects.select_related("user")
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

    def get_serializer_class(self):
        if self.action == "list":
            return ReadingListListSerializer
        if self.action == "items":
            return ReadingListItemSerializer
        return ReadingListReadSerializer

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


class CollectionViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Returns authenticated user's collection items.
    Requires authentication.

    retrieve:
    Returns details of a specific collection item (must belong to authenticated user).
    Requires authentication.
    """

    permission_classes = [IsAuthenticated]
    filterset_class = CollectionFilter

    def get_queryset(self):
        """Only return collection items belonging to the authenticated user."""
        return CollectionItem.objects.filter(user=self.request.user).select_related(
            "issue__series__series_type", "issue__series__publisher"
        )

    def get_serializer_class(self):
        if self.action == "list":
            return CollectionListSerializer
        return CollectionReadSerializer

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
        queryset = self.get_queryset()
        total_items = queryset.count()
        total_quantity = queryset.aggregate(Sum("quantity"))["quantity__sum"] or 0

        # Calculate total value
        total_value_result = queryset.aggregate(Sum("purchase_price"))
        total_value = total_value_result["purchase_price__sum"]

        # Reading statistics
        read_count = queryset.filter(is_read=True).count()
        unread_count = queryset.filter(is_read=False).count()

        format_counts = queryset.values("book_format").annotate(count=Count("id"))

        return Response(
            {
                "total_items": total_items,
                "total_quantity": total_quantity,
                "total_value": str(total_value) if total_value else "0.00",
                "read_count": read_count,
                "unread_count": unread_count,
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
