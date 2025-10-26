from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from sorl.thumbnail.admin.current import AdminImageMixin

from comicsdb.admin.util import AttributionInline
from comicsdb.models import Publisher


@admin.register(Publisher)
class PublisherAdmin(AdminImageMixin, SimpleHistoryAdmin):
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("created_on", "modified")
    list_display = ("name",)
    readonly_fields = ("modified",)
    fields = (
        "name",
        "slug",
        "modified",
        "founded",
        "country",
        "desc",
        "cv_id",
        "gcd_id",
        "image",
        "edited_by",
    )
    inlines = [AttributionInline]
