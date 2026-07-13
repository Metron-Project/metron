from django.db import models

from comicsdb.models.common import AbstractRating
from comicsdb.models.issue import Issue
from users.models import CustomUser


class IssueRating(AbstractRating):
    """User ratings for issues."""

    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="issue_ratings",
    )

    class Meta:
        unique_together = ["issue", "user"]
        indexes = [
            models.Index(fields=["issue", "user"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.issue}: {self.rating}"
