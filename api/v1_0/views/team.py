from rest_framework.parsers import FormParser, MultiPartParser

from api.cache import ModelLabel
from api.v1_0.serializers import (
    IssueListSerializer,
    TeamListSerializer,
    TeamReadSerializer,
    TeamSerializer,
)
from api.v1_0.views.mixins import CatalogViewSet, IssueListMixin
from comicsdb.filters.name import ComicVineFilter
from comicsdb.models import Team


class TeamViewSet(IssueListMixin, CatalogViewSet):
    """
    list:
    Return a list of all the teams.

    retrieve:
    Returns the information of an individual team.
    """

    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    serializer_classes = {
        "list": TeamListSerializer,
        "issue_list": IssueListSerializer,
        "retrieve": TeamReadSerializer,
    }
    filterset_class = ComicVineFilter
    cache_model_label = ModelLabel.TEAM
    parser_classes = (MultiPartParser, FormParser)
    # retrieve also embeds Creator/Universe names (TeamReadSerializer) that
    # don't cascade a `modified` bump onto this Team either. UNIVERSE is
    # tracked here: only ~180 rows site-wide and genuinely low-churn (~1.03
    # saves/row historically), so tying the key to it costs little. CREATOR
    # is deliberately NOT tracked -- ~17.8k rows and ~100x UNIVERSE's total
    # write volume (measured via historical save counts), so tying this key
    # to CREATOR's version would invalidate every cached Team detail on
    # essentially any creator create/edit/delete anywhere on the site,
    # reproducing the same cache-thrashing problem already confirmed in
    # production for ModelLabel.SERIES (see IssueViewSet). Creator-rename
    # staleness stays bounded (TTL-limited) as the tradeoff.
    cache_detail_dependent_labels = (ModelLabel.UNIVERSE,)

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "retrieve":
            queryset = queryset.prefetch_related("creators", "universes")
        return queryset
