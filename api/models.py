from django.conf import settings
from django.db import models


class ThrottleNotice(models.Model):
    """Records an email sent to an account whose API client keeps getting
    rate-limited without backing off. Used to avoid re-contacting the same
    account before a cooldown period has passed - see
    api/management/commands/notify_throttled_clients.py."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="throttle_notices"
    )
    days_throttled = models.PositiveSmallIntegerField()
    total_count = models.PositiveIntegerField()
    worst_day_count = models.PositiveIntegerField()
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.user} notified on {self.sent_at:%Y-%m-%d}"
