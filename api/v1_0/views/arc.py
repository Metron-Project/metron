from rest_framework import mixins, viewsets
from rest_framework.parsers import FormParser, MultiPartParser

from api.cache import ModelLabel
from api.v1_0.serializers import (
    ArcListSerializer,
    ArcReadSerializer,
    ArcSerializer,
    IssueListSerializer,
)
from api.v1_0.views.mixins import (
    CachedListModelMixin,
    ConditionalRetrieveModelMixin,
    IssueListMixin,
    UserTrackingMixin,
)
from comicsdb.filters.name import ComicVineFilter
from comicsdb.models import Arc


class ArcViewSet(
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
    Returns a list of all the story arcs.

    retrieve:
    Returns the information of an individual story arc.
    """

    queryset = Arc.objects.all()
    filterset_class = ComicVineFilter
    parser_classes = (MultiPartParser, FormParser)
    cache_model_label = ModelLabel.ARC
    # issue_list embeds fields from Issue rows (and their Series) that don't
    # cascade a `modified` bump onto this Arc except on M2M add/remove/
    # clear. ModelLabel.ISSUE/SERIES are deliberately NOT used as
    # cache_action_dependent_labels here: both are bumped by
    # update_series_modified_on_issue_save() on *every* issue write
    # anywhere on the site, so tying this 24h-TTL cache to either
    # invalidates every Arc's issue_list on essentially any issue edit
    # site-wide -- confirmed as a live problem for IssueViewSet's own
    # retrieve cache in production (see its cache_detail_dependent_labels
    # comment). A plain issue field edit can show stale here for up to
    # DETAIL_CACHE_TTL; that's the accepted tradeoff.

    def get_serializer_class(self):
        match self.action:
            case "list":
                return ArcListSerializer
            case "issue_list":
                return IssueListSerializer
            case "retrieve":
                return ArcReadSerializer
            case _:
                return ArcSerializer
