from django.contrib import admin

from wish_list.models import WishList, WishListItem


class WishListItemInline(admin.TabularInline):
    model = WishListItem
    extra = 1
    fields = ("issue", "status", "priority", "desired_grade", "max_price", "notes")
    autocomplete_fields = ["issue"]


@admin.register(WishList)
class WishListAdmin(admin.ModelAdmin):
    list_display = ("user", "is_private", "item_count", "modified", "created_on")
    list_filter = ("is_private", "created_on", "modified")
    search_fields = ("user__username",)
    readonly_fields = ("created_on", "modified")
    autocomplete_fields = ["user"]
    inlines = [WishListItemInline]

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.wish_list_items.count()


@admin.register(WishListItem)
class WishListItemAdmin(admin.ModelAdmin):
    list_display = (
        "wish_list",
        "issue",
        "status",
        "priority",
        "desired_grade",
        "max_price",
        "modified",
    )
    list_filter = ("status", "priority", "added_on", "modified")
    search_fields = ("wish_list__user__username", "issue__series__name", "notes")
    readonly_fields = ("added_on", "modified")
    autocomplete_fields = ["wish_list", "issue"]
    ordering = ("wish_list", "priority", "issue__series__sort_name")
