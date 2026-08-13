from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

DisplayTypes = [
    ("primary", _("Primary")),
    ("success", _("Success")),
    ("link", _("Link")),
    ("warning", _("Warning")),
    ("danger", _("Danger")),
]


class Announcement(models.Model):  # noqa: DJ008
    """The admin has something to say."""

    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    display_type = models.CharField(max_length=20, choices=DisplayTypes, default="primary")
    active = models.BooleanField(default=True)
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)

    @classmethod
    def active_announcements(cls):
        """Announcements that should be displayed."""
        now = timezone.now()
        return cls.objects.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now),
            Q(end_date__isnull=True) | Q(end_date__gte=now),
            active=True,
        )
