from django.db.models import Avg, Count, DecimalField, Prefetch
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser

from api.cache import ModelLabel
from api.v1_0.serializers import IssueListSerializer, IssueReadSerializer, IssueSerializer
from api.v1_0.views.mixins import (
    CatalogViewSet,
)
from comicsdb.filters.issue import IssueFilter
from comicsdb.models import Credits, Issue


class IssueViewSet(CatalogViewSet):
    """
    list:
    Return a list of all the issues.

    retrieve:
    Returns the information of an individual issue.

    Note: cover_hash is a Perceptual hashing created with
    ImageHash. https://github.com/JohannesBuchner/imagehash
    Use cover_hash_near (with an optional cover_hash_max_distance, default 10)
    to find issues whose cover hash is within that Hamming distance of a
    supplied hash, sorted closest first.
    """

    queryset = Issue.objects.all()
    serializer_class = IssueSerializer
    serializer_classes = {
        "list": IssueListSerializer,
        "retrieve": IssueReadSerializer,
    }
    filterset_class = IssueFilter
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    cache_model_label = ModelLabel.ISSUE
    # Each scanned cover yields a practically unique phash, so near-match
    # results would almost never be served from the cache.
    uncached_list_params = ("cover_hash_near",)
    # Issue retrieve embeds its Series/Publisher/Imprint/Arc/Character/Team/
    # Universe/Creator names, none of which cascade a `modified` bump onto
    # this Issue when renamed. Publisher/Imprint/Universe are tracked here --
    # Publisher/Imprint via their name-only counters (PUBLISHER_NAME/
    # IMPRINT_NAME), since tying the key to the every-save PUBLISHER/IMPRINT
    # counters orphaned every cached issue on any unrelated Publisher/Imprint
    # edit (confirmed in production: ~65% of issue detail keys were dead
    # generations). UNIVERSE stays on its every-save counter because the
    # embedded UniverseListSerializer includes `modified`; its write volume
    # is low enough that this costs little:
    # - SERIES is deliberately excluded even though it's also embedded --
    #   ModelLabel.SERIES is bumped by update_series_modified_on_issue_save()
    #   on *every* issue write anywhere (PublisherViewSet.series_list needs
    #   that), so including it here invalidated every cached issue detail
    #   response on essentially every issue edit site-wide, not just ones
    #   affecting this issue's own Series (confirmed in production: a
    #   single unrelated issue write elsewhere flipped an otherwise-stable
    #   X-Cache HIT to a MISS).
    # - Arc/Character/Team/Creator names are also embedded but excluded for
    #   the same reason -- their write volume (thousands to tens of
    #   thousands of historical saves, Character highest of all) would cost
    #   far more cache churn than the staleness they'd prevent.
    # Both cases accept staleness up to DETAIL_CACHE_TTL as the tradeoff.
    cache_detail_dependent_labels = (
        ModelLabel.PUBLISHER_NAME,
        ModelLabel.IMPRINT_NAME,
        ModelLabel.UNIVERSE,
    )

    def get_modified_queryset(self):
        # get_queryset() annotates average_rating/rating_count for the
        # retrieve action -- an aggregate that survives into (pk, modified)
        # values_list() as an extra JOIN + GROUP BY even though neither
        # annotated field is selected. This lookup only needs the row's own
        # pk/modified, so skip the annotation entirely.
        return Issue.objects.all()

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
            # average_rating/rating_count deliberately do NOT cascade a
            # `modified` bump on IssueRating changes (no such signal exists
            # anywhere in the codebase). Ratings churn far more than any
            # other field on a popular issue -- one vote per user, every
            # time -- so invalidating on every rating change would defeat
            # detail caching for exactly the issues most worth caching.
            # Accepted staleness up to DETAIL_CACHE_TTL for these two
            # fields specifically.
            .annotate(
                average_rating=Avg(
                    "ratings__rating", output_field=DecimalField(max_digits=3, decimal_places=2)
                ),
                rating_count=Count("ratings", distinct=True),
            )
        )
