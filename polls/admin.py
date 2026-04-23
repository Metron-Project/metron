from django.contrib import admin

from polls.models import Poll, PollChoice, PollVote


class PollChoiceInline(admin.TabularInline):
    model = PollChoice
    extra = 2
    fields = ("text", "order")


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "start_date", "end_date", "vote_count", "modified")
    list_filter = ("start_date", "end_date")
    search_fields = ("title", "description", "created_by__username")
    readonly_fields = ("created_on", "modified")
    autocomplete_fields = ["created_by"]
    inlines = [PollChoiceInline]

    def vote_count(self, obj):
        return obj.votes.count()

    vote_count.short_description = "Votes"


@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = ("poll", "choice", "user", "voted_on")
    list_filter = ("poll",)
    search_fields = ("poll__title", "user__username")
    readonly_fields = ("poll", "choice", "user", "voted_on")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
