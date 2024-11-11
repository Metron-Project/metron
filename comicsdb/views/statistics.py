from datetime import datetime

from chartkick.django import ColumnChart, PieChart
from django.core.cache import cache
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth, TruncYear
from django.shortcuts import render

from comicsdb.models import Arc, Character, Creator, Issue, Publisher, Series, Team

# Cache time to live is 30 minutes.
CACHE_TTL = 60 * 30


def _create_year_count_dict():
    years_count = cache.get("year_count_dict")
    if not years_count:
        years_count = (
            Issue.objects.annotate(year=TruncYear("created_on"))
            .values("year")
            .annotate(c=Count("year"))
            .order_by("year")
        )
        cache.set("year_count_dict", years_count, CACHE_TTL)

    return {year_count["year"].strftime("%Y"): year_count["c"] for year_count in years_count}


def _create_pub_dict() -> dict[str, int]:
    publishers = cache.get("publishers")
    if not publishers:
        publishers = Publisher.objects.annotate(num_issues=Count("series__issues")).values(
            "name", "num_issues"
        )
        cache.set("publishers", publishers, CACHE_TTL)
    return {publisher["name"]: publisher["num_issues"] for publisher in publishers}


def _create_monthly_issue_dict() -> dict[str, int]:
    monthly_issues = cache.get("monthly_issues")
    if not monthly_issues:
        monthly_issues = (
            Issue.objects.annotate(month=TruncMonth("created_on"))
            .values("month")
            .annotate(c=Count("month"))
            .order_by("-month")[:12]
        )
        cache.set("monthly_issues", monthly_issues, CACHE_TTL)

    return {issue["month"].strftime("%b"): issue["c"] for issue in monthly_issues[::-1]}


def _create_daily_issue_dict() -> dict[str, int]:
    daily_issues = cache.get("daily_issues")
    if not daily_issues:
        daily_issues = (
            Issue.objects.annotate(day=TruncDate("created_on"))
            .values("day")
            .annotate(c=Count("day"))
            .order_by("-day")[:30]
        )
        cache.set("daily_issues", daily_issues, CACHE_TTL)

    return {issue["day"].strftime("%m/%d"): issue["c"] for issue in daily_issues[::-1]}


def _create_creator_dict() -> dict[str, int]:
    creators = cache.get("creators")
    if not creators:
        creators = (
            Creator.objects.annotate(month=TruncMonth("created_on"))
            .values("month")
            .annotate(c=Count("month"))
            .order_by("-month")[:12]
        )
        cache.set("creators", creators, CACHE_TTL)

    return {creator["month"].strftime("%b"): creator["c"] for creator in creators[::-1]}


def _create_character_dict() -> dict[str, int]:
    characters = cache.get("characters")
    if not characters:
        characters = (
            Character.objects.annotate(month=TruncMonth("created_on"))
            .values("month")
            .annotate(c=Count("month"))
            .order_by("-month")[:12]
        )
        cache.set("characters", characters, CACHE_TTL)

    return {
        character["month"].strftime("%b"): character["c"] for character in characters[::-1]
    }


def statistics(request):
    # Resource totals
    cache_keys = [
        "stats_update_time",
        "publishers_total",
        "series_total",
        "issue_total",
        "characters_total",
        "creators_total",
        "teams_total",
        "arcs_total",
    ]
    cache_values = cache.get_many(cache_keys)

    update_time = cache_values.get("stats_update_time")
    if not update_time:
        update_time = datetime.now()
        cache.set("stats_update_time", update_time, CACHE_TTL)

    model_cache_map = {
        "publishers_total": Publisher,
        "series_total": Series,
        "issue_total": Issue,
        "characters_total": Character,
        "creators_total": Creator,
        "teams_total": Team,
        "arcs_total": Arc,
    }

    totals = {}
    for key, model in model_cache_map.items():
        totals[key] = cache_values.get(key)
        if totals[key] is None:
            totals[key] = model.objects.count()
            cache.set(key, totals[key], CACHE_TTL)

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
        _create_daily_issue_dict(), title="Number of Issues for the last 30 days"
    )
    monthly_chart = ColumnChart(
        _create_monthly_issue_dict(), title="Number of Issues Added by Month", thousands=","
    )
    creator_chart = ColumnChart(
        _create_creator_dict(), title="Number of Creators Added by Month"
    )
    character_chart = ColumnChart(
        _create_character_dict(),
        title="Number of Characters Added by Month",
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
            "publishers_total": totals["publishers_total"],
            "series_total": totals["series_total"],
            "issues_total": totals["issue_total"],
            "characters_total": totals["characters_total"],
            "creators_total": totals["creators_total"],
            "teams_total": totals["teams_total"],
            "arcs_total": totals["arcs_total"],
            "update_time": update_time,
        },
    )
