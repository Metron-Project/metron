from django.contrib import admin
from sorl.thumbnail.admin.current import AdminImageMixin

from comicsdb.admin.util import AttributionInline
from comicsdb.models import Creator


@admin.register(Creator)
class CreatorAdmin(AdminImageMixin, admin.ModelAdmin):
    search_fields = ("name", "alias")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("created_on", "modified")
    readonly_fields = ("modified",)
    field = (
        "name",
        "slug",
        "modified",
        "birth",
        "death",
        "alias",
        "desc",
        "cv_id",
        "gcd_id",
        "image",
    )
    actions_on_top = True
    inlines = [AttributionInline]
