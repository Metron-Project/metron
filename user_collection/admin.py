from django.contrib import admin

from user_collection.models import CollectionItem, ReadDate


class ReadDateInline(admin.TabularInline):
    """Inline admin for read dates."""

    model = ReadDate
    extra = 1
    readonly_fields = ("created_on",)
    fields = ("read_date", "created_on")
    ordering = ("-read_date",)


@admin.register(CollectionItem)
class CollectionItemAdmin(admin.ModelAdmin):
    """Admin interface for collection items."""

    list_display = (
        "user",
        "issue",
        "quantity",
        "book_format",
        "grade",
        "grading_company",
        "purchase_date",
        "purchase_price",
        "modified",
    )
    list_filter = ("book_format", "grading_company", "purchase_date", "created_on", "modified")
    search_fields = (
        "user__username",
        "issue__series__name",
        "purchase_store",
        "storage_location",
    )
    readonly_fields = ("created_on", "modified")
    autocomplete_fields = ["user", "issue"]
    inlines = [ReadDateInline]

    fieldsets = (
        (
            None,
            {"fields": ("user", "issue", "quantity", "book_format", "grade", "grading_company")},
        ),
        ("Purchase Information", {"fields": ("purchase_date", "purchase_price", "purchase_store")}),
        (
            "Reading Tracking",
            {
                "fields": ("is_read", "date_read", "rating"),
                "description": (
                    "Note: date_read is auto-synced from read dates. "
                    "Manage individual read dates below."
                ),
            },
        ),
        ("Storage", {"fields": ("storage_location", "notes")}),
        ("Timestamps", {"fields": ("created_on", "modified")}),
    )


@admin.register(ReadDate)
class ReadDateAdmin(admin.ModelAdmin):
    """Admin interface for read dates."""

    list_display = ("collection_item", "read_date", "created_on")
    list_filter = ("read_date", "created_on")
    search_fields = (
        "collection_item__user__username",
        "collection_item__issue__series__name",
    )
    readonly_fields = ("created_on",)
    autocomplete_fields = ["collection_item"]
    date_hierarchy = "read_date"
    ordering = ("-read_date",)
