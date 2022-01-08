from django.contrib import admin
from sorl.thumbnail.admin.current import AdminImageMixin

from comicsdb.models import Character


@admin.register(Character)
class CharacterAdmin(AdminImageMixin, admin.ModelAdmin):
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    # form view
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "desc",
                    "wikipedia",
                    "alias",
                    "image",
                    "edited_by",
                )
            },
        ),
        ("Related", {"fields": ("creators", "teams")}),
    )
    filter_horizontal = ("creators", "teams")