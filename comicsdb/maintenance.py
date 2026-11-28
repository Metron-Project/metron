"""Data maintenance checks.

Each check is a heuristic query that surfaces records which have likely gone stale since they
were entered (e.g. a Limited Series whose run has ended but is still marked Ongoing). Nothing
here changes data: the checks only list candidates for people to review and fix by hand, and an
item drops off its list once its data has been corrected.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Count, Max, QuerySet
from django.db.models.functions import Coalesce
from django.utils.functional import Promise
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from comicsdb.models import Issue, Series, SeriesType

# A Limited Series with no issue released within this many days is likely finished.
LIMITED_STALE_DAYS = 120
# An ongoing Single Issue series with no issue released within this many days is likely
# cancelled, completed, or on hiatus.
ONGOING_STALE_DAYS = 365
# How long after its store date an issue without credits is given before being flagged.
UNRELEASED_GRACE_DAYS = 60
# Only issues with a store date within this many days are checked for missing credits, since
# many older issues simply haven't had their credits entered yet.
UNRELEASED_WINDOW_DAYS = 730


@dataclass(frozen=True)
class MaintenanceCheck:
    slug: str
    title: str | Promise
    description: str | Promise
    suggested_fix: str | Promise
    kind: str  # "series" or "issue"
    queryset: Callable[[date], QuerySet]


def _stale_series(series_type_id: int, stale_days: int, today: date) -> QuerySet:
    """Ongoing series of the given type whose most recent issue is older than ``stale_days``.

    A series with a future-dated issue has a ``last_date`` after ``today``, so it's excluded.
    """
    return (
        Series.objects.filter(series_type_id=series_type_id, status=Series.Status.ONGOING)
        .annotate(
            last_date=Max(Coalesce("issues__store_date", "issues__cover_date")),
            issue_count=Count("issues", distinct=True),
        )
        .filter(last_date__lt=today - timedelta(days=stale_days))
        .select_related("publisher", "series_type")
        .order_by("last_date", "sort_name", "id")
    )


def stale_limited_series(today: date) -> QuerySet:
    return _stale_series(SeriesType.LIMITED_SERIES, LIMITED_STALE_DAYS, today)


def stale_ongoing_series(today: date) -> QuerySet:
    return _stale_series(SeriesType.SINGLE_ISSUE, ONGOING_STALE_DAYS, today)


def unreleased_issues(today: date) -> QuerySet:
    """Issues whose store date has passed but that still have no credits."""
    return (
        Issue.objects.filter(
            store_date__gte=today - timedelta(days=UNRELEASED_WINDOW_DAYS),
            store_date__lt=today - timedelta(days=UNRELEASED_GRACE_DAYS),
        )
        .annotate(credit_count=Count("credits"))
        .filter(credit_count=0)
        .select_related("series", "series__series_type")
        .order_by("-store_date", "series__sort_name", "id")
    )


CHECKS: dict[str, MaintenanceCheck] = {
    check.slug: check
    for check in (
        MaintenanceCheck(
            slug="stale-limited-series",
            title=_("Limited Series Possibly Completed"),
            description=format_lazy(
                _(
                    "Limited Series still marked Ongoing whose most recent issue was released "
                    "more than {days} days ago, with no future issues scheduled."
                ),
                days=LIMITED_STALE_DAYS,
            ),
            suggested_fix=_(
                "If the series has finished its run, change its status to Completed. If more "
                "issues are coming, add them or set the status to Hiatus."
            ),
            kind="series",
            queryset=stale_limited_series,
        ),
        MaintenanceCheck(
            slug="stale-ongoing-series",
            title=_("Ongoing Series With No Recent Issues"),
            description=format_lazy(
                _(
                    "Single Issue series still marked Ongoing whose most recent issue was released "
                    "more than {days} days ago, with no future issues scheduled."
                ),
                days=ONGOING_STALE_DAYS,
            ),
            suggested_fix=_(
                "Change the series status to Completed, Cancelled, or Hiatus as appropriate."
            ),
            kind="series",
            queryset=stale_ongoing_series,
        ),
        MaintenanceCheck(
            slug="unreleased-issues",
            title=_("Issues Possibly Never Released"),
            description=format_lazy(
                _(
                    "Issues whose in store date passed more than {days} days ago but that still "
                    "have no credits. These may have been solicited and then delayed or cancelled."
                ),
                days=UNRELEASED_GRACE_DAYS,
            ),
            suggested_fix=_(
                "If the issue was released, add its credits. If it was delayed or cancelled, "
                "correct or remove its in store date and note this in the description."
            ),
            kind="issue",
            queryset=unreleased_issues,
        ),
    )
}
