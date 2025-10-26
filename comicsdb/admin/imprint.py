from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from sorl.thumbnail.admin import AdminImageMixin

from comicsdb.admin.util import AttributionInline
from comicsdb.models import Imprint


@admin.register(Imprint)
class ImprintAdmin(AdminImageMixin, SimpleHistoryAdmin):
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "publisher")
    list_filter = ("created_on", "modified")
    readonly_fields = ("created_on", "modified")
    fields = (
        "name",
        "slug",
        "desc",
        "founded",
        "publisher",
        "cv_id",
        "gcd_id",
        "image",
        "edited_by",
    )
    inlines = [AttributionInline]
