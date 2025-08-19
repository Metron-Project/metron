from django.db.models import Prefetch
from django.http import Http404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
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


class ArcViewSet(
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

    def perform_create(self, serializer: ArcSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: ArcSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)

    @action(detail=True)
    def issue_list(self, request, pk=None):
        """
        Returns a list of issues for a story arc.
        """
        arc = self.get_object()
        queryset = arc.issues.select_related("series", "series__series_type").order_by(
            "cover_date", "series", "number"
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = IssueListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404


class CharacterViewSet(
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

    def perform_create(self, serializer: CharacterSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: CharacterSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)

    @action(detail=True)
    def issue_list(self, request, pk=None):
        """
        Returns a list of issues for a character.
        """
        character = self.get_object()
        queryset = character.issues.select_related("series", "series__series_type").order_by(
            "cover_date", "series", "number"
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = IssueListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404


class CreatorViewSet(
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

    def perform_create(self, serializer: CreatorSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: CreatorSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)


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

    def get_serializer_class(self):
        return CreditSerializer

    def create(self, request, *args, **kwargs) -> Response:
        serializer: CreditSerializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ImprintViewSet(
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

    def get_serializer_class(self):
        match self.action:
            case "list":
                return ImprintListSerializer
            case "retrieve":
                return ImprintReadSerializer
            case _:
                return ImprintSerializer

    def perform_create(self, serializer: ImprintSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: ImprintSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)


class IssueViewSet(
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
        "series", "series__series_type", "rating"
    ).prefetch_related(
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

    def perform_create(self, serializer: IssueSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: IssueSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)


class PublisherViewSet(
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

    def perform_create(self, serializer: PublisherSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: PublisherSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)

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
    serializer_class = SeriesSerializer
    filterset_class = SeriesFilter

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

        if self.request.method in {"POST", "PUT", "PATCH"} and not self.request.data.get(
            "imprint"
        ):
            series_request_data = self.request.data.copy()
            series_request_data["imprint"] = None
            kwargs["data"] = series_request_data
        return serializer_class(*args, **kwargs)

    def perform_create(self, serializer: SeriesSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: SeriesSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)

    @action(detail=True)
    def issue_list(self, request, pk=None):
        """
        Returns a list of issues for a series.
        """
        series = self.get_object()
        queryset = series.issues.all()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = IssueListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404


class SeriesTypeViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    list:
    Returns a list of the Series Types available.
    """

    queryset = SeriesType.objects.all()
    serializer_class = SeriesTypeSerializer
    filterset_class = NameFilter


class TeamViewSet(
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

    def perform_create(self, serializer: TeamSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: TeamSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)

    @action(detail=True)
    def issue_list(self, request, pk=None):
        """
        Returns a list of issues for a character.
        """
        team = self.get_object()
        queryset = team.issues.select_related("series", "series__series_type").order_by(
            "cover_date", "series", "number"
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = IssueListSerializer(page, many=True, context={"request": request})
            return self.get_paginated_response(serializer.data)
        raise Http404


class UniverseViewSet(
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

    def get_serializer_class(self):
        match self.action:
            case "list":
                return UniverseListSerializer
            case "retrieve":
                return UniverseReadSerializer
            case _:
                return UniverseSerializer

    def perform_create(self, serializer: UniverseSerializer) -> None:
        serializer.save(edited_by=self.request.user, created_by=self.request.user)
        return super().perform_create(serializer)

    def perform_update(self, serializer: UniverseSerializer) -> None:
        serializer.save(edited_by=self.request.user)
        return super().perform_update(serializer)


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

    def get_serializer_class(self):
        return VariantSerializer
