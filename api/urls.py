from django.urls import include, path
from rest_framework import routers

from api.views import (
    ArcViewSet,
    CharacterViewSet,
    CollectionViewSet,
    CreatorViewSet,
    CreditViewset,
    ImprintViewSet,
    IssueViewSet,
    PublisherViewSet,
    PullListViewSet,
    ReadingListViewSet,
    RoleViewset,
    SeriesTypeViewSet,
    SeriesViewSet,
    TeamViewSet,
    UniverseViewSet,
    VariantViewset,
    WishListViewSet,
)

ROUTER = routers.DefaultRouter()
ROUTER.register("arc", ArcViewSet)
ROUTER.register("character", CharacterViewSet)
ROUTER.register("collection", CollectionViewSet, basename="collection")
ROUTER.register("creator", CreatorViewSet)
ROUTER.register("credit", CreditViewset)
ROUTER.register("imprint", ImprintViewSet)
ROUTER.register("issue", IssueViewSet)
ROUTER.register("publisher", PublisherViewSet)
ROUTER.register("pull_list", PullListViewSet, basename="pull_list")
ROUTER.register("reading_list", ReadingListViewSet, basename="reading_list")
ROUTER.register("wish_list", WishListViewSet, basename="wish_list")
ROUTER.register("role", RoleViewset)
ROUTER.register("series", SeriesViewSet)
ROUTER.register("series_type", SeriesTypeViewSet)
ROUTER.register("team", TeamViewSet)
ROUTER.register("universe", UniverseViewSet)
ROUTER.register("variant", VariantViewset)

app_name = "api"
urlpatterns = [path("", include(ROUTER.urls))]
