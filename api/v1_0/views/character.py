from rest_framework import mixins, viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from api.cache import ModelLabel
from api.v1_0.serializers import (
    CharacterListSerializer,
    CharacterReadSerializer,
    CharacterSerializer,
    IssueListSerializer,
)
from api.v1_0.views.mixins import (
    CachedListModelMixin,
    ConditionalRetrieveModelMixin,
    IssueListMixin,
    UserTrackingMixin,
)
from comicsdb.filters.name import ComicVineFilter
from comicsdb.models import Character


class CharacterViewSet(
    UserTrackingMixin,
    IssueListMixin,
    mixins.CreateModelMixin,
    ConditionalRetrieveModelMixin,
    CachedListModelMixin,
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
    cache_model_label = ModelLabel.CHARACTER
    # retrieve also embeds Creator/Team/Universe names (CharacterReadSerializer)
    # that don't cascade a `modified` bump onto this Character either.
    # TEAM and UNIVERSE are tracked here: low-to-moderate row counts and
    # write volume (measured via historical save counts: ~3.1k saves for
    # Team, ~180 for Universe), so tying the key to either costs little.
    # CREATOR is deliberately NOT tracked -- ~17.8k rows and ~100x
    # UNIVERSE's write volume, so tying this key to CREATOR's version would
    # invalidate every cached Character detail on essentially any creator
    # create/edit/delete anywhere on the site, reproducing the same
    # cache-thrashing problem already confirmed in production for
    # ModelLabel.SERIES (see IssueViewSet). Creator-rename staleness stays
    # bounded (TTL-limited) as the tradeoff.
    cache_detail_dependent_labels = (ModelLabel.TEAM, ModelLabel.UNIVERSE)

    # issue_list embeds fields from Issue rows (and their Series) that don't
    # cascade a `modified` bump onto this Character except on M2M add/
    # remove/clear. ModelLabel.ISSUE/SERIES are deliberately NOT used as
    # cache_action_dependent_labels here either, for the same reason as
    # CREATOR above: both are bumped by update_series_modified_on_issue_save()
    # on *every* issue write anywhere on the site, so tying this 24h-TTL
    # cache to either invalidates every Character's issue_list on
    # essentially any issue edit site-wide.

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
