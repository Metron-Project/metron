from django.db import models
from django.db.models.functions import Now
from django.urls import reverse
from djmoney.models.fields import MoneyField

from comicsdb.models.issue import Issue
from users.models import CustomUser


class CollectionItem(models.Model):
    """Model for tracking a user's comic book collection."""

    class BookFormat(models.TextChoices):
        PRINT = "PRINT", "Print"
        DIGITAL = "DIGITAL", "Digital"
        BOTH = "BOTH", "Both"

    # Relationships
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="collection_items",
        help_text="The user who owns this collection item",
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="in_collections",
        help_text="The issue in this collection",
    )

    # Collection metadata
    quantity = models.PositiveSmallIntegerField(default=1, help_text="Number of copies owned")
    book_format = models.CharField(
        max_length=10,
        choices=BookFormat.choices,
        default=BookFormat.PRINT,
        help_text="Format of the comic (print, digital, or both)",
    )

    # Purchase information
    purchase_date = models.DateField(
        null=True, blank=True, help_text="Date when the issue was purchased"
    )
    purchase_price = MoneyField(
        "Purchase Price",
        max_digits=7,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Price paid for this issue",
    )
    purchase_store = models.CharField(
        max_length=255, blank=True, help_text="Store or vendor where purchased"
    )

    # Storage and notes
    storage_location = models.CharField(
        max_length=255, blank=True, help_text="Physical location where the issue is stored"
    )
    notes = models.TextField(blank=True, help_text="Additional notes about this collection item")

    # Reading tracking
    is_read = models.BooleanField(default=False, help_text="Whether the issue has been read")
    date_read = models.DateField(null=True, blank=True, help_text="Date when the issue was read")

    # Timestamps
    created_on = models.DateTimeField(db_default=Now())
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user", "issue__series__sort_name", "issue__cover_date"]
        unique_together = ["user", "issue"]
        indexes = [
            models.Index(fields=["user", "issue"], name="user_issue_idx"),
            models.Index(fields=["user", "purchase_date"], name="user_purchase_date_idx"),
            models.Index(fields=["user", "book_format"], name="user_format_idx"),
            models.Index(fields=["user", "is_read"], name="user_is_read_idx"),
        ]
        verbose_name = "Collection Item"
        verbose_name_plural = "Collection Items"

    def __str__(self) -> str:
        return f"{self.user.username}: {self.issue} (x{self.quantity})"

    def get_absolute_url(self):
        return reverse("user_collection:detail", args=[self.pk])
