from datetime import datetime

from chartkick.django import ColumnChart, PieChart
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.shortcuts import render

from comicsdb.models import Arc, Character, Creator, Issue, Publisher, Series, Team


def _create_year_count_dict():
    years_count = (
        Issue.objects.annotate(year=TruncYear("created_on"))
        .values("year")
        .annotate(c=Count("year"))
        .order_by("year")
    )
    return {year_count["year"].strftime("%Y"): year_count["c"] for year_count in years_count}


def _create_pub_dict() -> dict[str, int]:
    publishers = Publisher.objects.annotate(num_issues=Count("series__issues")).values(
        "name", "num_issues"
    )
    return {publisher["name"]: publisher["num_issues"] for publisher in publishers}


def _create_monthly_issue_dict() -> dict[str, int]:
    monthly_issues = (
        Issue.objects.annotate(month=TruncMonth("created_on"))
        .values("month")
        .annotate(c=Count("month"))
        .order_by("-month")[:12]
    )
    return {issue["month"].strftime("%b"): issue["c"] for issue in monthly_issues[::-1]}


def _create_daily_issue_dict() -> dict[str, int]:
    daily_issues = (
        Issue.objects.annotate(day=TruncDate("created_on"))
        .values("day")
        .annotate(c=Count("day"))
        .order_by("-day")[:30]
    )
    return {issue["day"].strftime("%m/%d"): issue["c"] for issue in daily_issues[::-1]}


def _create_creator_dict() -> dict[str, int]:
    creators = (
        Creator.objects.annotate(month=TruncMonth("created_on"))
        .values("month")
        .annotate(c=Count("month"))
        .order_by("-month")[:12]
    )
    return {creator["month"].strftime("%b"): creator["c"] for creator in creators[::-1]}


def _create_character_dict() -> dict[str, int]:
    characters = (
        Character.objects.annotate(month=TruncMonth("created_on"))
        .values("month")
        .annotate(c=Count("month"))
        .order_by("-month")[:12]
    )
    return {character["month"].strftime("%b"): character["c"] for character in characters[::-1]}


def statistics_totals(request):
    """HTMX endpoint for database totals - always returns fresh data."""
    update_time = datetime.now()

    totals = {
        "publishers_total": Publisher.objects.count(),
        "series_total": Series.objects.count(),
        "issues_total": Issue.objects.count(),
        "characters_total": Character.objects.count(),
        "creators_total": Creator.objects.count(),
        "teams_total": Team.objects.count(),
        "arcs_total": Arc.objects.count(),
    }

    return render(
        request,
        "comicsdb/partials/statistics_totals.html",
        {
            "update_time": update_time,
            **totals,
        },
    )


def statistics_charts(request):
    """HTMX endpoint for statistics charts - always returns fresh data."""
    pub_chart = PieChart(
        _create_pub_dict(),
        title="Percentage of Issues by Publisher",
        thousands=",",
        legend=False,
    )
    year_chart = PieChart(
        _create_year_count_dict(), title="Number of Issues Added per Year", thousands=","
    )
    daily_chart = ColumnChart(
        _create_daily_issue_dict(),
        title="Number of Issues for the last 30 days",
        thousands=",",
    )
    monthly_chart = ColumnChart(
        _create_monthly_issue_dict(), title="Number of Issues Added by Month", thousands=","
    )
    creator_chart = ColumnChart(
        _create_creator_dict(),
        title="Number of Creators Added by Month",
        thousands=",",
    )
    character_chart = ColumnChart(
        _create_character_dict(),
        title="Number of Characters Added by Month",
        thousands=",",
    )

    return render(
        request,
        "comicsdb/partials/statistics_charts.html",
        {
            "publisher_count": pub_chart,
            "year_count": year_chart,
            "daily_chart": daily_chart,
            "monthly_chart": monthly_chart,
            "creator_chart": creator_chart,
            "character_chart": character_chart,
        },
    )


def statistics(request):
    """Main statistics page - uses HTMX for live updates."""
    update_time = datetime.now()

    # Get initial data for first page load
    totals = {
        "publishers_total": Publisher.objects.count(),
        "series_total": Series.objects.count(),
        "issues_total": Issue.objects.count(),
        "characters_total": Character.objects.count(),
        "creators_total": Creator.objects.count(),
        "teams_total": Team.objects.count(),
        "arcs_total": Arc.objects.count(),
    }

    # Time based statistics
    pub_chart = PieChart(
        _create_pub_dict(),
        title="Percentage of Issues by Publisher",
        thousands=",",
        legend=False,
    )
    year_chart = PieChart(
        _create_year_count_dict(), title="Number of Issues Added per Year", thousands=","
    )
    daily_chart = ColumnChart(
        _create_daily_issue_dict(),
        title="Number of Issues for the last 30 days",
        thousands=",",
    )
    monthly_chart = ColumnChart(
        _create_monthly_issue_dict(), title="Number of Issues Added by Month", thousands=","
    )
    creator_chart = ColumnChart(
        _create_creator_dict(),
        title="Number of Creators Added by Month",
        thousands=",",
    )
    character_chart = ColumnChart(
        _create_character_dict(),
        title="Number of Characters Added by Month",
        thousands=",",
    )

    return render(
        request,
        "comicsdb/statistics.html",
        {
            "publisher_count": pub_chart,
            "year_count": year_chart,
            "daily_chart": daily_chart,
            "monthly_chart": monthly_chart,
            "creator_chart": creator_chart,
            "character_chart": character_chart,
            "update_time": update_time,
            **totals,
        },
    )
