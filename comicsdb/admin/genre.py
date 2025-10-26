from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from comicsdb.models.genre import Genre


@admin.register(Genre)
class GenreAdmin(SimpleHistoryAdmin):
    search_fields = ("name",)
    readonly_fields = ("modified",)
    fields = ("name", "desc", "modified")
