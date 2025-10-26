from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from sorl.thumbnail.admin.current import AdminImageMixin

from comicsdb.models import Arc


@admin.register(Arc)
class ArcAdmin(AdminImageMixin, SimpleHistoryAdmin):
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("created_on", "modified")
    field = ("name", "slug", "desc", "cv_id", "gcd_id", "image")
