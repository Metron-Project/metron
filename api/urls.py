from django.urls import include, path
from rest_framework import routers

from api.views import (
    ArcViewSet,
    CharacterViewSet,
    CreatorViewSet,
    CreditViewset,
    ImprintViewSet,
    IssueViewSet,
    PublisherViewSet,
    RoleViewset,
    SeriesTypeViewSet,
    SeriesViewSet,
    TeamViewSet,
    UniverseViewSet,
    VariantViewset,
)

ROUTER = routers.DefaultRouter()
ROUTER.register("arc", ArcViewSet)
ROUTER.register("character", CharacterViewSet)
ROUTER.register("creator", CreatorViewSet)
ROUTER.register("credit", CreditViewset)
ROUTER.register("imprint", ImprintViewSet)
ROUTER.register("issue", IssueViewSet)
ROUTER.register("publisher", PublisherViewSet)
ROUTER.register("role", RoleViewset)
ROUTER.register("series", SeriesViewSet)
ROUTER.register("series_type", SeriesTypeViewSet)
ROUTER.register("team", TeamViewSet)
ROUTER.register("universe", UniverseViewSet)
ROUTER.register("variant", VariantViewset)

app_name = "api"
urlpatterns = [path("", include(ROUTER.urls))]
