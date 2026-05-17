from django.contrib import admin

from pull_list.models import PullList, PullListSeries


class PullListSeriesInline(admin.TabularInline):
    model = PullListSeries
    extra = 1
    fields = ("series", "added_on")
    readonly_fields = ("added_on",)
    autocomplete_fields = ["series"]


@admin.register(PullList)
class PullListAdmin(admin.ModelAdmin):
    list_display = ("user", "series_count", "modified", "created_on")
    list_filter = ("created_on", "modified")
    search_fields = ("user__username",)
    readonly_fields = ("created_on", "modified")
    autocomplete_fields = ["user"]
    inlines = [PullListSeriesInline]

    @admin.display(description="Series")
    def series_count(self, obj):
        return obj.series.count()


@admin.register(PullListSeries)
class PullListSeriesAdmin(admin.ModelAdmin):
    list_display = ("pull_list", "series", "added_on")
    search_fields = ("pull_list__user__username", "series__name")
    autocomplete_fields = ["pull_list", "series"]
    readonly_fields = ("added_on",)
    ordering = ("pull_list", "series__sort_name")
