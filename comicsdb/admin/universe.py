from django.contrib import admin
from sorl.thumbnail.admin import AdminImageMixin

from comicsdb.admin.util import AttributionInline
from comicsdb.models import Universe


@admin.register(Universe)
class UniverseAdmin(AdminImageMixin, admin.ModelAdmin):
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ["publisher"]
    list_display = ("name", "designation", "publisher", "created_on", "modified")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "publisher",
                    "name",
                    "slug",
                    "designation",
                    "desc",
                    "cv_id",
                    "gcd_id",
                    "image",
                    "edited_by",
                )
            },
        ),
    )
    inlines = [AttributionInline]
