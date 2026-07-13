from django.contrib import admin

from issue_ratings.models import IssueRating


@admin.register(IssueRating)
class IssueRatingAdmin(admin.ModelAdmin):
    list_display = ("issue", "user", "rating", "modified")
    list_filter = ("rating", "created_on")
    search_fields = ("issue__series__name", "user__username")
    readonly_fields = ("created_on", "modified")
    autocomplete_fields = ["issue", "user"]
