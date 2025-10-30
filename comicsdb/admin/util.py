from datetime import date, datetime, timedelta

from django.contrib import admin
from django.contrib.contenttypes.admin import GenericStackedInline

from comicsdb.models.attribution import Attribution


class AttributionInline(GenericStackedInline):
    model = Attribution
    extra = 1


class CreatedOnDateListFilter(admin.SimpleListFilter):
    title = "created on"

    parameter_name = "created_on"

    def lookups(self, request, model_admin):
        return (
            ("today", "Today"),
            ("yesterday", "Yesterday"),
            ("7day", "Past 7 days"),
            ("thisMonth", "This month"),
            ("thisYear", "This year"),
        )

    def queryset(self, request, queryset):
        today = date.today()
        yesterday = datetime.now() - timedelta(days=1)
        last_week = datetime.now() - timedelta(days=7)

        match self.value():
            case "today":
                return queryset.filter(created_on__date=today)
            case "yesterday":
                return queryset.filter(created_on__date=yesterday.date())
            case "7day":
                return queryset.filter(created_on__date__gte=last_week.date())
            case "thisMonth":
                return queryset.filter(created_on__year=today.year, created_on__month=today.month)
            case "thisYear":
                return queryset.filter(created_on__year=today.year)
            case _:
                return None
