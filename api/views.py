from django.db.models import Count, Prefetch, Q
from django.http import Http404
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from api.v1_0.serializers import (
    ArcListSerializer,
    ArcSerializer,
    CharacterListSerializer,
    CharacterReadSerializer,
    CharacterSerializer,
    CreatorListSerializer,
    CreatorSerializer,
    CreditSerializer,
    ImprintListSerializer,
    ImprintReadSerializer,
    ImprintSerializer,
    IssueListSerializer,
    IssueReadSerializer,
    IssueSerializer,
    PublisherListSerializer,
    PublisherSerializer,
    ReadingListListSerializer,
    ReadingListReadSerializer,
    ReadingListSerializer,
    RoleSerializer,
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
from users.models import CustomUser


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
    UserTrackingMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    list:
    Returns a list of reading lists based on user permissions.
    - Unauthenticated users: Only public lists
    - Authenticated users: Public lists + own lists
    - Admin users: Public lists + own lists + Metron's lists

    retrieve:
    Returns the information of an individual reading list.

    create:
    Create a new reading list. User will be automatically set to the authenticated user.

    update:
    Update a reading list's information. Only the owner or admin (for Metron's lists) can update.

    destroy:
    Delete a reading list. Only the owner or admin (for Metron's lists) can delete.
    """

    queryset = ReadingList.objects.all()
    filterset_class = ReadingListFilter

    def get_queryset(self):
        """Filter reading lists based on user permissions and visibility rules."""
        queryset = ReadingList.objects.select_related("user").annotate(issue_count=Count("issues"))

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
        match self.action:
            case "list":
                return ReadingListListSerializer
            case "retrieve":
                return ReadingListReadSerializer
            case _:
                return ReadingListSerializer

    def perform_create(self, serializer):
        """Set the user to the current authenticated user on create."""
        serializer.save(user=self.request.user)

    def check_object_permissions(self, request, obj):
        """Check if user has permission to modify the reading list."""
        super().check_object_permissions(request, obj)

        # Allow if user is the owner
        if obj.user == request.user:
            return

        # Allow if user is admin and managing Metron's lists
        if request.user.is_staff:
            try:
                metron_user = CustomUser.objects.get(username="Metron")
                if obj.user == metron_user:
                    return
            except CustomUser.DoesNotExist:
                pass

        # For update and delete actions, deny permission
        if self.action in ["update", "partial_update", "destroy"]:
            raise PermissionDenied("You do not have permission to modify this reading list.")


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
