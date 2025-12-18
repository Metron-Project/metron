from django.db import models
from django.db.models.signals import pre_save
from django.urls import reverse

from comicsdb.models.common import CommonInfo, pre_save_slug
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from users.models import CustomUser


class ReadingList(CommonInfo):
    """Model for user-created reading lists of comic issues.

    Each reading list is owned by a single user who has exclusive
    edit permissions for that list.
    """

    class AttributionSource(models.TextChoices):
        """Source attribution choices."""

        CBRO = "CBRO", "Comic Book Reading Orders"
        CMRO = "CMRO", "Complete Marvel Reading Orders"
        CBH = "CBH", "Comic Book Herald"
        CBT = "CBT", "Comic Book Treasury"
        MG = "MG", "Marvel Guides"
        HTLC = "HTLC", "How To Love Comics"
        LOCG = "LOCG", "League of ComicGeeks"
        OTHER = "OTHER", "Other"

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
    attribution_source = models.CharField(
        max_length=10,
        choices=AttributionSource.choices,
        blank=True,
        help_text="Source where this reading list information was obtained",
    )
    attribution_url = models.URLField(
        blank=True,
        help_text="URL of the specific page where this reading list was obtained",
    )
    issues = models.ManyToManyField(
        Issue,
        through="ReadingListItem",
        related_name="in_reading_lists",
        blank=True,
    )

    class Meta:
        ordering = ["name", "attribution_source", "user"]
        unique_together = ["user", "name"]

    def __str__(self) -> str:
        result = f"{self.user.username}: {self.name}"
        if self.attribution_source:
            result += f" ({self.get_attribution_source_display()})"  # type: ignore[attr-defined]
        return result

    def get_absolute_url(self):
        return reverse("reading-list:detail", args=[self.slug])

    @property
    def start_year(self) -> int | None:
        """Get the earliest year from the reading list's issues."""
        earliest_issue = (
            self.reading_list_items.select_related("issue").order_by("issue__cover_date").first()
        )
        return earliest_issue.issue.cover_date.year if earliest_issue else None

    @property
    def end_year(self) -> int | None:
        """Get the latest year from the reading list's issues."""
        latest_issue = (
            self.reading_list_items.select_related("issue").order_by("-issue__cover_date").first()
        )
        return latest_issue.issue.cover_date.year if latest_issue else None

    @property
    def publishers(self):
        """Get all unique publishers from the reading list's issues."""
        return (
            Publisher.objects.filter(series__issues__reading_list_items__reading_list=self)
            .distinct()
            .order_by("name")
        )


class ReadingListItem(models.Model):
    """Through model for ordering issues within a reading list."""

    class IssueType(models.TextChoices):
        """Issue type choices for reading list items."""

        PROLOGUE = "PROLOGUE", "Prologue"
        CORE = "CORE", "Core Issue"
        TIE_IN = "TIE_IN", "Tie-In"
        EPILOGUE = "EPILOGUE", "Epilogue"

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
    issue_type = models.CharField(
        max_length=10,
        choices=IssueType.choices,
        blank=True,
        help_text="Optional categorization of this issue's role in the reading list",
    )

    class Meta:
        ordering = ["reading_list", "order"]
        unique_together = ["reading_list", "issue"]
        indexes = [
            models.Index(fields=["reading_list", "order"], name="reading_list_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.reading_list.name} - {self.issue} (Order: {self.order})"


class ReadingListRating(models.Model):
    """User ratings for reading lists."""

    reading_list = models.ForeignKey(
        ReadingList,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="reading_list_ratings",
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="Star rating (1-5) for this reading list",
    )
    created_on = models.DateTimeField(db_default=models.functions.Now())
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["reading_list", "user"]
        indexes = [
            models.Index(fields=["reading_list", "user"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.reading_list.name}: {self.rating}"


pre_save.connect(pre_save_slug, sender=ReadingList)
