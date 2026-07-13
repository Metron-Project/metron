from django.db import models
from django.db.models.functions import Now

from comicsdb.models.issue import Issue
from users.models import CustomUser


class IssueRating(models.Model):
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
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="Star rating (1-5) for this issue",
    )
    created_on = models.DateTimeField(db_default=Now())
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["issue", "user"]
        indexes = [
            models.Index(fields=["issue", "user"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.issue}: {self.rating}"
