import operator
from functools import reduce

import django_filters as df
from django import forms
from django.core.validators import RegexValidator
from django.db.models import F, Func, IntegerField, Q, Value

from comicsdb.models import Issue
from comicsdb.models.issue import PHASH_REGEX, HexToBigint

#: Default and maximum Hamming distance (in bits, of 64) for the ``cover_hash_near`` filter.
# The default targets digital comic files: in a sample of 595 tagged digital comics, 98.8% of
# covers were within 8 bits of the correct issue, while the closest wrong cover in the full
# ~184k-hash corpus was 8-16 bits off (mostly 12-14). At 10 the correct issue was the only result
# 94.5% of the time; at 16 every query also returned unrelated covers. Camera scans are noisier
# (typically 6-16 bits off, Metron discussion #680), so callers can raise the distance up to the
# maximum. Results are sorted closest first.
DEFAULT_COVER_HASH_DISTANCE = 10
MAX_COVER_HASH_DISTANCE = 24

validate_phash = RegexValidator(PHASH_REGEX, "Enter a 16-character hexadecimal perceptual hash.")


class IssueSeriesName(df.rest_framework.CharFilter):
    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(operator.and_, (Q(series__name__unaccent__icontains=q) for q in query_list))
            )
        return super().filter(qs, value)


class IssueSeriesQuickSearch(df.rest_framework.CharFilter):
    """Multi-word search across the issue's series name and alternative names."""

    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(
                    operator.and_,
                    (
                        Q(series__name__unaccent__icontains=q)
                        | Q(series__alt_names__joined__icontains=q)
                        for q in query_list
                    ),
                )
            )
        return super().filter(qs, value)


class CoverHashDistance(Func):
    """Hamming distance between two 64-bit phashes stored as signed bigints.

    Renders as ``bit_count((a # b)::bit(64))`` (PostgreSQL 14+), where ``#`` is integer XOR.
    """

    template = "bit_count((%(expressions)s)::bit(64))"
    arg_joiner = " # "
    arity = 2
    output_field = IntegerField()


class IntegerFilter(df.rest_framework.NumberFilter):
    field_class = forms.IntegerField


class NumberInFilter(df.rest_framework.BaseInFilter, df.rest_framework.NumberFilter):
    pass


class IssueCoverIdentifier(df.CharFilter):
    """Find each parent issue once when its main cover or a variant matches."""

    def filter(self, qs, value):
        if not value:
            return super().filter(qs, value)
        return qs.filter(
            Q(**{f"{self.field_name}__{self.lookup_expr}": value})
            | Q(**{f"variants__{self.field_name}__{self.lookup_expr}": value})
        ).distinct()


class IssueFilter(df.rest_framework.FilterSet):
    cover_year = df.rest_framework.NumberFilter(
        label="Cover Year", field_name="cover_date", lookup_expr="year"
    )
    cover_month = df.rest_framework.NumberFilter(
        label="Cover Month", field_name="cover_date", lookup_expr="month"
    )
    number = df.rest_framework.CharFilter(
        label="Issue Number", field_name="number", lookup_expr="iexact"
    )
    alt_number = df.rest_framework.CharFilter(
        label="Alternate Number", field_name="alt_number", lookup_expr="iexact"
    )
    publisher_name = df.rest_framework.CharFilter(
        label="Publisher Name", field_name="series__publisher__name", lookup_expr="icontains"
    )
    publisher_id = df.rest_framework.NumberFilter(
        label="Publisher Metron ID", field_name="series__publisher__id", lookup_expr="exact"
    )
    imprint_name = df.rest_framework.CharFilter(
        label="Imprint Name", field_name="series__imprint__name", lookup_expr="icontains"
    )
    imprint_id = df.rest_framework.NumberFilter(
        label="Imprint Metron ID", field_name="series__imprint__id", lookup_expr="exact"
    )
    series_name = IssueSeriesName(
        label="Series Name", field_name="series__name", lookup_expr="icontains"
    )
    series_alt_names = df.rest_framework.CharFilter(
        label="Series Alternative Name",
        field_name="series__alt_names",
        lookup_expr="joined__icontains",
    )
    series_q = IssueSeriesQuickSearch(label="Quick search across series name and alternative names")
    series_id = df.rest_framework.NumberFilter(
        label="Series Metron ID", field_name="series__id", lookup_expr="exact"
    )
    series_volume = df.rest_framework.NumberFilter(
        label="Series Volume Number", field_name="series__volume", lookup_expr="exact"
    )
    cover_date_range = df.rest_framework.DateFromToRangeFilter("cover_date")
    store_date_range = df.rest_framework.DateFromToRangeFilter("store_date")
    foc_date_range = df.rest_framework.DateFromToRangeFilter("foc_date")
    series_year_began = df.rest_framework.NumberFilter(
        label="Series Beginning Year", field_name="series__year_began", lookup_expr="exact"
    )
    modified_gt = df.rest_framework.DateTimeFilter(
        label="Greater than Modified DateTime", field_name="modified", lookup_expr="gt"
    )
    rating = df.rest_framework.CharFilter(
        label="Rating", field_name="rating__name", lookup_expr="iexact"
    )
    sku = IssueCoverIdentifier(
        label="Distributor SKU (main or variant cover)", field_name="sku", lookup_expr="iexact"
    )
    upc = IssueCoverIdentifier(
        label="UPC Code (main or variant cover)", field_name="upc", lookup_expr="iexact"
    )
    upc_starts_with = df.rest_framework.CharFilter(
        label="UPC Code starts with (e.g. the 12-digit UPC-A read by a mobile scanner "
        "that strips the 5-digit EAN supplemental)",
        field_name="upc",
        lookup_expr="startswith",
    )
    cv_id = df.rest_framework.NumberFilter(
        label="Comic Vine ID", field_name="cv_id", lookup_expr="exact"
    )
    missing_cv_id = df.rest_framework.BooleanFilter(field_name="cv_id", lookup_expr="isnull")
    gcd_id = df.rest_framework.NumberFilter(
        label="Grand Comics Database ID", field_name="gcd_id", lookup_expr="exact"
    )
    missing_gcd_id = df.rest_framework.BooleanFilter(field_name="gcd_id", lookup_expr="isnull")
    cover_hash = df.rest_framework.CharFilter(
        label="Cover Hash", field_name="cover_hash", lookup_expr="iexact"
    )
    cover_hash_near = df.rest_framework.CharFilter(
        label="Cover Hash near match (16-character hex phash; results sorted closest first)",
        method="filter_cover_hash_near",
        validators=[validate_phash],
    )
    cover_hash_max_distance = IntegerFilter(
        label=f"Maximum Hamming distance for cover_hash_near "
        f"(0-{MAX_COVER_HASH_DISTANCE}, default {DEFAULT_COVER_HASH_DISTANCE})",
        method="filter_cover_hash_max_distance",
        min_value=0,
        max_value=MAX_COVER_HASH_DISTANCE,
    )
    creator_id = df.rest_framework.NumberFilter(
        label="Creator Metron ID", field_name="creators__id", lookup_expr="exact", distinct=True
    )
    character_id = df.rest_framework.NumberFilter(
        label="Character Metron ID", field_name="characters__id", lookup_expr="exact", distinct=True
    )
    team_id = df.rest_framework.NumberFilter(
        label="Team Metron ID", field_name="teams__id", lookup_expr="exact", distinct=True
    )
    universe_id = df.rest_framework.NumberFilter(
        label="Universe Metron ID", field_name="universes__id", lookup_expr="exact", distinct=True
    )
    role_id = NumberInFilter(
        label="Role Metron ID", field_name="credits__role__id", lookup_expr="in", distinct=True
    )
    desc_is_solicitation = df.rest_framework.BooleanFilter(
        label="Description is the publisher's solicitation text"
    )

    class Meta:
        model = Issue
        fields = ["store_date", "foc_date"]

    def filter_cover_hash_near(self, qs, name, value: str):
        if not value:
            return qs
        max_distance = self.form.cleaned_data.get("cover_hash_max_distance")
        if max_distance is None:
            max_distance = DEFAULT_COVER_HASH_DISTANCE
        # Convert the query hash with the same SQL as the generated column, so the two can't
        # disagree; PostgreSQL folds it to a constant once per query.
        distance = CoverHashDistance(F("cover_hash_bits"), HexToBigint(Value(value)))
        # Fetch the matching ids first, as their own query: it is an index-only scan of
        # issue_cover_hash_bits_idx, and the outer query then becomes a primary-key lookup.
        # Inlined as an IN (subquery), the planner can't estimate how few rows match and
        # falls back to scanning the whole issue table.
        ids = list(
            Issue.objects.filter(cover_hash_bits__isnull=False)
            .alias(cover_hash_distance=distance)
            .filter(cover_hash_distance__lte=max_distance)
            .order_by()
            .values_list("pk", flat=True)
        )
        return (
            qs.filter(pk__in=ids)
            .annotate(cover_hash_distance=distance)
            .order_by("cover_hash_distance", *Issue._meta.ordering)
        )

    @staticmethod
    def filter_cover_hash_max_distance(qs, name, value: int):
        # Only modifies cover_hash_near, which reads it from the form's cleaned data.
        return qs


class IssueViewFilter(df.FilterSet):
    """Filter for issue list views with search capabilities."""

    # Quick search for series names
    q = IssueSeriesName(label="Quick Search")

    cover_year = df.NumberFilter(label="Cover Year", field_name="cover_date", lookup_expr="year")
    cover_month = df.NumberFilter(label="Cover Month", field_name="cover_date", lookup_expr="month")
    number = df.rest_framework.CharFilter(
        label="Issue Number", field_name="number", lookup_expr="iexact"
    )
    alt_number = df.rest_framework.CharFilter(
        label="Alternate Number", field_name="alt_number", lookup_expr="iexact"
    )
    publisher_name = df.CharFilter(
        label="Publisher Name", field_name="series__publisher__name", lookup_expr="icontains"
    )
    publisher_id = df.NumberFilter(
        label="Publisher Metron ID", field_name="series__publisher__id", lookup_expr="exact"
    )
    series_name = IssueSeriesName(label="Series Name")
    series_id = df.NumberFilter(
        label="Series Metron ID", field_name="series__id", lookup_expr="exact"
    )
    series_volume = df.NumberFilter(
        label="Series Volume Number", field_name="series__volume", lookup_expr="exact"
    )
    series_type = df.NumberFilter(
        label="Series Type", field_name="series__series_type__id", lookup_expr="exact"
    )
    store_date = df.DateFromToRangeFilter("store_date")
    foc_date = df.DateFromToRangeFilter("foc_date")
    series_year_began = df.NumberFilter(
        label="Series Beginning Year", field_name="series__year_began", lookup_expr="exact"
    )
    sku = IssueCoverIdentifier(
        label="Distributor SKU (main or variant cover)", field_name="sku", lookup_expr="iexact"
    )
    upc = IssueCoverIdentifier(
        label="UPC Code (main or variant cover)", field_name="upc", lookup_expr="iexact"
    )
    cv_id = df.rest_framework.NumberFilter(
        label="Comic Vine ID", field_name="cv_id", lookup_expr="exact"
    )
    gcd_id = df.rest_framework.NumberFilter(
        label="Grand Comics Database ID", field_name="gcd_id", lookup_expr="exact"
    )
    desc_is_solicitation = df.BooleanFilter(label="Solicitation Description")

    class Meta:
        model = Issue
        fields = ["q"]
