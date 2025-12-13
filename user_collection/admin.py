from django.contrib import admin

from user_collection.models import CollectionItem


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

    fieldsets = (
        (
            None,
            {"fields": ("user", "issue", "quantity", "book_format", "grade", "grading_company")},
        ),
        ("Purchase Information", {"fields": ("purchase_date", "purchase_price", "purchase_store")}),
        ("Storage", {"fields": ("storage_location", "notes")}),
        ("Timestamps", {"fields": ("created_on", "modified")}),
    )
