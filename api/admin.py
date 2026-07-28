from django.contrib import admin

from api.models import ThrottleNotice


@admin.register(ThrottleNotice)
class ThrottleNoticeAdmin(admin.ModelAdmin):
    list_display = ("user", "days_throttled", "total_count", "worst_day_count", "sent_at")
    list_filter = ("sent_at",)
    search_fields = ("user__username", "user__email")
    ordering = ("-sent_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
