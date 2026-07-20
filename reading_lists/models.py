from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Avg, Count, Max, Min, Q
from django.db.models.signals import pre_save
from django.urls import reverse
from sorl.thumbnail import ImageField

from comicsdb.models.common import CommonInfo, pre_save_slug
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from users.models import CustomUser

READING_LIST_EDITOR_GROUP = "reading list editor"
METRON_USERNAME = "Metron"


class ReadingListQuerySet(models.QuerySet):
    """Shared filtering/annotation logic used by multiple reading list views."""

    def visible_to(self, user):
        """Restrict to reading lists the given user is allowed to see.

        Public lists are always visible. A user can also see their own lists.
        Staff and 'reading list editor' group members can additionally see
        lists owned by the shared 'Metron' account.
        """
        if not user.is_authenticated:
            return self.filter(is_private=False)

        is_editor = user.is_staff or user.groups.filter(name=READING_LIST_EDITOR_GROUP).exists()
        if is_editor:
            metron_user = CustomUser.objects.filter(username=METRON_USERNAME).first()
            if metron_user:
                return self.filter(Q(is_private=False) | Q(user=user) | Q(user=metron_user))

        return self.filter(Q(is_private=False) | Q(user=user))

    def with_list_stats(self):
        """Annotate with issue count, rating stats, and cover-date year range."""
        return self.annotate(
            issue_count=Count("issues", distinct=True),
            average_rating=Avg("ratings__rating"),
            rating_count=Count("ratings", distinct=True),
            start_year_annotated=Min("reading_list_items__issue__cover_date__year"),
            end_year_annotated=Max("reading_list_items__issue__cover_date__year"),
        )


class ReadingList(CommonInfo):
    """Model for user-created reading lists of comic issues.

    Each reading list is owned by a single user who has exclusive
    edit permissions for that list.
    """

    objects = ReadingListQuerySet.as_manager()

    class ListType(models.TextChoices):
        """Reading list type choices."""

        CREATOR = "CREATOR", "Creator"
        EVENT = "EVENT", "Event"
        STORY = "STORY", "Story"
        CHARACTERS = "CHARACTERS", "Characters"
        TEAMS = "TEAMS", "Teams"
        MASTER = "MASTER", "Master"

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
    list_type = models.CharField(
        max_length=10,
        choices=ListType.choices,
        default=ListType.EVENT,
        help_text="The type of reading list",
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
    image = ImageField(upload_to="reading_list/%Y/%m/%d/", blank=True)
    issues = models.ManyToManyField(
        Issue,
        through="ReadingListItem",
        related_name="in_reading_lists",
        blank=True,
    )
    previous = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="The reading list that comes before this one in a reading order",
    )
    next = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="The reading list that comes after this one in a reading order",
    )

    class Meta:
        ordering = ["name", "attribution_source", "user"]
        unique_together = ["user", "name", "attribution_source"]

    def __str__(self) -> str:
        result = f"{self.user.username}: {self.name}"
        if self.attribution_source:
            result += f" ({self.get_attribution_source_display()})"  # type: ignore[attr-defined]
        return result

    def clean(self):
        super().clean()
        if self.previous_id and self.previous_id == self.pk:
            raise ValidationError({"previous": "A reading list cannot be its own previous list."})
        if self.next_id and self.next_id == self.pk:
            raise ValidationError({"next": "A reading list cannot be its own next list."})
        if self.previous_id and self.next_id and self.previous_id == self.next_id:
            raise ValidationError("The previous and next reading lists must be different.")

    def save(self, *args, **kwargs):
        old_previous_id = None
        old_next_id = None
        if self.pk:
            old = ReadingList.objects.filter(pk=self.pk).values("previous_id", "next_id").first()
            if old:
                old_previous_id, old_next_id = old["previous_id"], old["next_id"]

        super().save(*args, **kwargs)

        # Keep the reverse side of the previous/next relationship in sync, so
        # linking A -> next=B also links B -> previous=A (and vice versa).
        if self.next_id != old_next_id:
            if old_next_id:
                ReadingList.objects.filter(pk=old_next_id, previous_id=self.pk).update(
                    previous=None
                )
            if self.next_id:
                ReadingList.objects.filter(pk=self.next_id).exclude(previous_id=self.pk).update(
                    previous=self
                )

        if self.previous_id != old_previous_id:
            if old_previous_id:
                ReadingList.objects.filter(pk=old_previous_id, next_id=self.pk).update(next=None)
            if self.previous_id:
                ReadingList.objects.filter(pk=self.previous_id).exclude(next_id=self.pk).update(
                    next=self
                )

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
        default=1,
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
