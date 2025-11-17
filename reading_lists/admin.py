from django.contrib import admin

from reading_lists.models import ReadingList, ReadingListItem


class ReadingListItemInline(admin.TabularInline):
    """Inline admin for reading list items."""

    model = ReadingListItem
    extra = 1
    fields = ("issue", "order")
    autocomplete_fields = ["issue"]


@admin.register(ReadingList)
class ReadingListAdmin(admin.ModelAdmin):
    """Admin interface for reading lists."""

    list_display = ("name", "user", "is_private", "issue_count", "modified", "created_on")
    list_filter = ("is_private", "created_on", "modified")
    search_fields = ("name", "desc", "user__username")
    readonly_fields = ("slug", "created_on", "modified")
    autocomplete_fields = ["user"]

    fieldsets = (
        (None, {"fields": ("name", "slug", "desc", "user", "is_private")}),
        ("Metadata", {"fields": ("cv_id", "gcd_id", "created_on", "modified")}),
    )

    inlines = [ReadingListItemInline]

    def issue_count(self, obj):
        """Display the number of issues in the list."""
        return obj.issues.count()

    issue_count.short_description = "Issues"


@admin.register(ReadingListItem)
class ReadingListItemAdmin(admin.ModelAdmin):
    """Admin interface for reading list items."""

    list_display = ("reading_list", "issue", "order")
    search_fields = ("reading_list__name", "issue__series__name")
    autocomplete_fields = ["reading_list", "issue"]
    ordering = ("reading_list", "order")
