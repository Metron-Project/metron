"""Statistics and charts for a user's collection (stats page and API ``stats`` action)."""

from datetime import datetime, timedelta

from chartkick.django import BarChart, ColumnChart, PieChart
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils.translation import gettext as _

from comicsdb.models.credits import Credits
from user_collection.models import CollectionItem, ReadDate

# Role.name values (exact database names -- do not translate) counted as writers/artists
# for the "Top Writers" / "Top Artists" charts.
WRITER_ROLES = ("Writer", "Script", "Story", "Plot")
ARTIST_ROLES = (
    "Artist",
    "Penciller",
    "Illustrator",
    "Layouts",
    "Breakdowns",
    "Inker",
    "Embellisher",
    "Finishes",
    "Ink Assists",
)
TOP_CREATORS_LIMIT = 10
TOP_SERIES_LIMIT = 10
DAILY_READS_DAYS = 30
MONTHLY_READS_MONTHS = 12


def collection_summary(user) -> dict:
    """Totals, read/unread counts and the per-format breakdown for ``user``'s collection.

    ``total_value`` is the summed purchase price, or ``None`` when no item has one.
    ``format_counts`` is a queryset of ``{"book_format", "count"}`` rows.
    """
    queryset = CollectionItem.objects.filter(user=user)
    totals = queryset.aggregate(
        total_items=Count("id"),
        total_quantity=Sum("quantity"),
        total_value=Sum("purchase_price"),
        read_count=Count("id", filter=Q(is_read=True)),
        unread_count=Count("id", filter=Q(is_read=False)),
    )
    return {
        **totals,
        "total_quantity": totals["total_quantity"] or 0,
        "format_counts": queryset.values("book_format").annotate(count=Count("id")),
    }


def top_series(user):
    """The series ``user`` has the most collection items from."""
    return (
        CollectionItem.objects.filter(user=user)
        .values("issue__series__name", "issue__series__id")
        .annotate(count=Count("id"))
        .order_by("-count")[:TOP_SERIES_LIMIT]
    )


def _distribution_chart(rows, field, title, label=None):
    """Pie chart of ``{field, count}`` rows; ``label`` maps a raw value to its slice name."""
    label = label or (lambda value: value or _("Unknown"))
    return PieChart(
        {label(row[field]): row["count"] for row in rows},
        title=title,
        thousands=",",
        legend="bottom",
    )


def _count_by(queryset, field):
    return queryset.values(field).annotate(count=Count("id")).order_by("-count")


def _top_creators_chart(issue_ids, roles, title):
    """Bar chart of the creators credited (in ``roles``) on the most of ``issue_ids``."""
    rows = (
        Credits.objects.filter(issue_id__in=issue_ids, role__name__in=roles)
        .values("creator__name")
        .annotate(count=Count("issue", distinct=True))
        .order_by("-count")[:TOP_CREATORS_LIMIT]
    )
    return BarChart(
        {row["creator__name"]: row["count"] for row in rows},
        title=title,
        thousands=",",
        library={"scales": {"x": {"ticks": {"precision": 0}}}},
    )


def _reading_charts(user):
    """Column charts of issues read per day (last 30 days) and per month (last 12)."""
    read_dates = ReadDate.objects.filter(collection_item__user=user)

    daily_reads = (
        read_dates.annotate(day=TruncDate("read_date"))
        .values("day")
        .annotate(c=Count("day"))
        .order_by("-day")[:DAILY_READS_DAYS]
    )
    daily_counts = {row["day"]: row["c"] for row in daily_reads}
    today = datetime.now().date()
    days = [today - timedelta(days=i) for i in range(DAILY_READS_DAYS - 1, -1, -1)]
    daily_chart = ColumnChart(
        {day.strftime("%m/%d"): daily_counts.get(day, 0) for day in days},
        title=_("Issues Read (Last 30 Days)"),
        thousands=",",
    )

    monthly_reads = (
        read_dates.annotate(month=TruncMonth("read_date"))
        .values("month")
        .annotate(c=Count("month"))
        .order_by("-month")[:MONTHLY_READS_MONTHS]
    )
    monthly_chart = ColumnChart(
        {row["month"].strftime("%b %Y"): row["c"] for row in monthly_reads[::-1]},
        title=_("Issues Read (Last 12 Months)"),
        thousands=",",
    )
    return daily_chart, monthly_chart


def collection_charts(user, format_counts) -> dict:
    """The stats page charts, keyed by their template context names.

    ``format_counts`` is ``collection_summary(user)["format_counts"]``, reused
    for the format chart so it isn't queried separately.
    """
    queryset = CollectionItem.objects.filter(user=user)
    format_names = dict(CollectionItem.BookFormat.choices)
    issue_ids = queryset.values_list("issue_id", flat=True)
    daily_chart, monthly_chart = _reading_charts(user)

    return {
        "publisher_chart": _distribution_chart(
            _count_by(queryset, "issue__series__publisher__name"),
            "issue__series__publisher__name",
            _("Issues by Publisher"),
        ),
        "series_type_chart": _distribution_chart(
            _count_by(queryset, "issue__series__series_type__name"),
            "issue__series__series_type__name",
            _("Issues by Series Type"),
        ),
        "format_chart": _distribution_chart(
            format_counts,
            "book_format",
            _("Issues by Format"),
            label=lambda value: format_names.get(value, _("Unknown")),
        ),
        "reading_daily_chart": daily_chart,
        "reading_monthly_chart": monthly_chart,
        "top_writers_chart": _top_creators_chart(issue_ids, WRITER_ROLES, _("Top Writers")),
        "top_artists_chart": _top_creators_chart(issue_ids, ARTIST_ROLES, _("Top Artists")),
    }
