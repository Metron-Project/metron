from django.db import models
from django.db.models.signals import pre_save
from django.urls import reverse

from comicsdb.models.common import CommonInfo, pre_save_slug
from comicsdb.models.issue import Issue
from users.models import CustomUser


class ReadingList(CommonInfo):
    """Model for user-created reading lists of comic issues.

    Each reading list is owned by a single user who has exclusive
    edit permissions for that list.
    """

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reading_lists",
        help_text="The user who owns this reading list",
    )
    is_private = models.BooleanField(
        default=False,
        help_text="Whether this list is private (only visible to the owner)",
    )
    issues = models.ManyToManyField(
        Issue,
        through="ReadingListItem",
        related_name="in_reading_lists",
        blank=True,
    )

    class Meta:
        ordering = ["user", "name"]
        unique_together = ["user", "name"]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.name}"

    def get_absolute_url(self):
        return reverse("reading-list:detail", args=[self.slug])


class ReadingListItem(models.Model):
    """Through model for ordering issues within a reading list."""

    reading_list = models.ForeignKey(
        ReadingList,
        on_delete=models.CASCADE,
        related_name="reading_list_items",
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="reading_list_items",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Position of this issue in the reading list",
    )

    class Meta:
        ordering = ["reading_list", "order"]
        unique_together = ["reading_list", "issue"]
        indexes = [
            models.Index(fields=["reading_list", "order"], name="reading_list_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.reading_list.name} - {self.issue} (Order: {self.order})"


pre_save.connect(pre_save_slug, sender=ReadingList)
