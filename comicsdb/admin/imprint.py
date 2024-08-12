from django.contrib import admin
from sorl.thumbnail.admin import AdminImageMixin

from comicsdb.admin.util import AttributionInline
from comicsdb.models import Imprint


@admin.register(Imprint)
class ImprintAdmin(AdminImageMixin, admin.ModelAdmin):
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    list_display = ("name", "publisher")
    list_filter = ("created_on", "modified")
    readonly_fields = ("created_on", "modified")
    fields = ("name", "slug", "desc", "founded", "publisher", "image", "edited_by")
    inlines = [AttributionInline]
