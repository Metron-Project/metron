from django.db import models
from django.db.models import Avg, Case, Count, F, IntegerField, Prefetch, Q, Sum, When
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from djmoney.money import Money
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_condition import last_modified

from api.v1_0.serializers import (
    ArcListSerializer,
    ArcSerializer,
    CharacterListSerializer,
    CharacterReadSerializer,
    CharacterSerializer,
    CollectionListSerializer,
    CollectionRatingUpdateSerializer,
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
from api.v1_0.serializers.pull_list import (
    PullListIssueSerializer,
    PullListReadSerializer,
    PullListSeriesSerializer,
)
from api.v1_0.serializers.wish_list import (
    AcquireWishListItemSerializer,
    WishListAddItemSerializer,
    WishListItemListSerializer,
    WishListItemReadSerializer,
    WishListSerializer,
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
from pull_list.models import PullList, PullListSeries
from reading_lists.models import ReadingList
from user_collection.models import CollectionItem
from users.models import CustomUser
from wish_list.models import WishList, WishListItem


class ReadingListItemsPagination(PageNumberPagination):
    """Custom pagination for reading list items with 50 items per page."""

    page_size = 50


class CachedObjectMixin:
    def get_object(self):
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object()

        return self._cached_object


class ConditionalRetrieveModelMixin(CachedObjectMixin, mixins.RetrieveModelMixin):
    def retrieve(self, request, *args, **kwargs):
        retrieve = last_modified(last_modified_func=self._retrieve_last_modified)(super().retrieve)

        return retrieve(self, request, *args, **kwargs)

    def _retrieve_last_modified(self, *args, **kwargs):
        obj = self.get_object()

        if obj and getattr(obj, "modified", None):
            return obj.modified

        return None


class UserTrackingMixin:
    """Mixin to automatically track user edits in create and update operations."""

    def perform_create(self, serializer):
        serializer.save(edited_by=self.request.user, created_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(edited_by=self.request.user)


class IssueListMixin(CachedObjectMixin):
    """Mixin to provide a standard issue_list action for related models."""

    def get_issue_queryset(self, obj):
        """Override to customize the issue queryset for a specific viewset."""
        return obj.issues.select_related("series", "series__series_type").order_by(
            "cover_date", "series", "number"
        )

    @extend_schema(responses={200: IssueListSerializer(many=True)}, filters=False)
    @action(detail=True)
    def issue_list(self, request, *args, **kwargs):
        issue_list = last_modified(last_modified_func=self._issue_list_last_modified)(
            self._issue_list
        )

        return issue_list(self, request, *args, **kwargs)

    def _issue_list(self, request, *args, **kwargs):
        """Returns a list of issues for this object."""
        obj = self.get_object()
        queryset = self.get_issue_queryset(obj)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = IssueListSerializer(page, many=True, context={"request": self.request})
            return self.get_paginated_response(serializer.data)
        raise Http404

    def _issue_list_last_modified(self, *args, **kwargs):
        obj = self.get_object()

        if obj and getattr(obj, "modified", None):
            return obj.modified

        return None


class ArcViewSet(
    UserTrackingMixin,
    IssueListMixin,
    mixins.CreateModelMixin,
    ConditionalRetrieveModelMixin,
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
    ConditionalRetrieveModelMixin,
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
    ConditionalRetrieveModelMixin,
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
    ConditionalRetrieveModelMixin,
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

    queryset = Imprint.objects.all()
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
    ConditionalRetrieveModelMixin,
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

    queryset = Issue.objects.all()
    filterset_class = IssueFilter
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        if self.action == "list":
            return Issue.objects.select_related("series", "series__series_type")
        return (
            Issue.objects.select_related(
                "series",
                "series__series_type",
                "series__publisher",
                "series__imprint",
                "rating",
            )
            .prefetch_related(
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
            .annotate(
                average_rating=Avg("ratings__rating"),
                rating_count=Count("ratings", distinct=True),
            )
        )

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
    ConditionalRetrieveModelMixin,
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

    queryset = Publisher.objects.all()
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

    @extend_schema(responses={200: SeriesListSerializer(many=True)}, filters=False)
    @action(detail=True)
    def series_list(self, request, pk=None):
        """
        Returns a list of series for a publisher.
        """
        publisher = self.get_object()
        queryset = (
            publisher.series.select_related("series_type")
            .annotate(num_issues=Count("issues", distinct=True))
            .order_by("sort_name", "year_began")
        )
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
    ConditionalRetrieveModelMixin,
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
        match self.action:
            case "list":
                queryset = queryset.annotate(num_issues=Count("issues", distinct=True)).order_by(
                    "sort_name", "year_began"
                )
            case "retrieve":
                queryset = (
                    queryset.select_related("imprint")
                    .prefetch_related("genres", "associated")
                    .annotate(num_issues=Count("issues", distinct=True))
                )
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

        if (
            self.action != "partial_update"
            and "data" in kwargs
            and not kwargs["data"].get("imprint")
        ):
            data = kwargs["data"].copy()
            data["imprint"] = None
            kwargs["data"] = data
        return serializer_class(*args, **kwargs)

    def get_issue_queryset(self, obj):
        return obj.issues.select_related("series", "series__series_type").order_by(
            "cover_date", "series", "number"
        )


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
    ConditionalRetrieveModelMixin,
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
    ConditionalRetrieveModelMixin,
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
    ConditionalRetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
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
    """

    permission_classes = [IsAuthenticated]
    filterset_class = CollectionFilter

    def get_queryset(self):
        """Only return collection items belonging to the authenticated user."""
        return (
            CollectionItem.objects.filter(user=self.request.user)
            .select_related("issue__series__series_type", "issue__series__publisher")
            .prefetch_related("read_dates")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return CollectionListSerializer
        if self.action in ("update", "partial_update"):
            return CollectionRatingUpdateSerializer
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
