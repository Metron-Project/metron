from django.contrib import admin

from comicsdb.models import Series, SeriesType


@admin.register(Series)
class SeriesAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "year_began")
    list_filter = ("created_on", "modified", "series_type", "status", "publisher")
    prepopulated_fields = {"slug": ("name", "year_began")}
    autocomplete_fields = ["associated"]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "sort_name",
                    "publisher",
                    "volume",
                    "year_began",
                    "year_end",
                    "series_type",
                    "status",
                    "associated",
                    "desc",
                    "cv_id",
                    "gcd_id",
                    "edited_by",
                )
            },
        ),
        ("Related", {"fields": ("genres",)}),
    )
    filter_horizontal = ("genres",)


@admin.register(SeriesType)
class SeriesTypeAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    fields = ("name", "notes")
