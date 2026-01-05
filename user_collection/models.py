from decimal import Decimal

from django.db import models
from django.db.models.functions import Now
from django.urls import reverse
from djmoney.models.fields import MoneyField

from comicsdb.models.issue import Issue
from users.models import CustomUser

# CGC Grading Scale choices
GRADE_CHOICES = [
    (Decimal("10.0"), "10.0 (Gem Mint)"),
    (Decimal("9.9"), "9.9 (Mint)"),
    (Decimal("9.8"), "9.8 (NM/M - Near Mint/Mint)"),
    (Decimal("9.6"), "9.6 (NM+ - Near Mint+)"),
    (Decimal("9.4"), "9.4 (NM - Near Mint)"),
    (Decimal("9.2"), "9.2 (NM- - Near Mint-)"),
    (Decimal("9.0"), "9.0 (VF/NM - Very Fine/Near Mint)"),
    (Decimal("8.5"), "8.5 (VF+ - Very Fine+)"),
    (Decimal("8.0"), "8.0 (VF - Very Fine)"),
    (Decimal("7.5"), "7.5 (VF- - Very Fine-)"),
    (Decimal("7.0"), "7.0 (FN/VF - Fine/Very Fine)"),
    (Decimal("6.5"), "6.5 (FN+ - Fine+)"),
    (Decimal("6.0"), "6.0 (FN - Fine)"),
    (Decimal("5.5"), "5.5 (FN- - Fine-)"),
    (Decimal("5.0"), "5.0 (VG/FN - Very Good/Fine)"),
    (Decimal("4.5"), "4.5 (VG+ - Very Good+)"),
    (Decimal("4.0"), "4.0 (VG - Very Good)"),
    (Decimal("3.5"), "3.5 (VG- - Very Good-)"),
    (Decimal("3.0"), "3.0 (GD/VG - Good/Very Good)"),
    (Decimal("2.5"), "2.5 (GD+ - Good+)"),
    (Decimal("2.0"), "2.0 (GD - Good)"),
    (Decimal("1.8"), "1.8 (GD- - Good-)"),
    (Decimal("1.5"), "1.5 (FR/GD - Fair/Good)"),
    (Decimal("1.0"), "1.0 (FR - Fair)"),
    (Decimal("0.5"), "0.5 (PR - Poor)"),
]


class CollectionItem(models.Model):
    """Model for tracking a user's comic book collection."""

    class BookFormat(models.TextChoices):
        PRINT = "PRINT", "Print"
        DIGITAL = "DIGITAL", "Digital"
        BOTH = "BOTH", "Both"

    class GradingCompany(models.TextChoices):
        CGC = "CGC", "CGC (Certified Guaranty Company)"
        CBCS = "CBCS", "CBCS (Comic Book Certification Service)"
        PGX = "PGX", "PGX (Professional Grading Experts)"

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

    # Grading information
    grade = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        choices=GRADE_CHOICES,
        help_text="Comic book grade (CGC scale)",
    )
    grading_company = models.CharField(
        max_length=10,
        choices=GradingCompany.choices,
        blank=True,
        default="",
        help_text="Professional grading company (leave blank for user-assessed grade)",
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
    date_read = models.DateTimeField(
        null=True, blank=True, help_text="Date and time when the issue was read"
    )
    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=[(i, i) for i in range(1, 6)],
        help_text="Star rating (1-5) for this issue",
    )

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
            models.Index(fields=["user", "grade"], name="user_grade_idx"),
            models.Index(fields=["user", "grading_company"], name="user_grading_company_idx"),
        ]
        verbose_name = "Collection Item"
        verbose_name_plural = "Collection Items"

    def __str__(self) -> str:
        return f"{self.user.username}: {self.issue} (x{self.quantity})"

    def get_absolute_url(self):
        return reverse("user_collection:detail", args=[self.pk])
