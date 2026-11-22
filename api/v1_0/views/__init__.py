"""Viewsets for the v1.0 REST API, one module per resource."""

from api.v1_0.views.arc import ArcViewSet
from api.v1_0.views.character import CharacterViewSet
from api.v1_0.views.collection import CollectionViewSet
from api.v1_0.views.creator import CreatorViewSet, CreditViewset, RoleViewset
from api.v1_0.views.imprint import ImprintViewSet
from api.v1_0.views.issue import IssueViewSet
from api.v1_0.views.publisher import PublisherViewSet
from api.v1_0.views.pull_list import PullListViewSet
from api.v1_0.views.reading_list import ReadingListViewSet
from api.v1_0.views.series import SeriesTypeViewSet, SeriesViewSet
from api.v1_0.views.team import TeamViewSet
from api.v1_0.views.universe import UniverseViewSet
from api.v1_0.views.variant import VariantViewset
from api.v1_0.views.wish_list import WishListViewSet

__all__ = [
    "ArcViewSet",
    "CharacterViewSet",
    "CollectionViewSet",
    "CreatorViewSet",
    "CreditViewset",
    "ImprintViewSet",
    "IssueViewSet",
    "PublisherViewSet",
    "PullListViewSet",
    "ReadingListViewSet",
    "RoleViewset",
    "SeriesTypeViewSet",
    "SeriesViewSet",
    "TeamViewSet",
    "UniverseViewSet",
    "VariantViewset",
    "WishListViewSet",
]
