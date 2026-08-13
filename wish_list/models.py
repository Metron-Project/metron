from django.db import models
from django.db.models.functions import Now
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from djmoney.models.fields import MoneyField

from comicsdb.models.issue import Issue
from user_collection.models import GRADE_CHOICES
from users.models import CustomUser


class WishList(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="wish_list",
    )
    modified = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(db_default=Now())

    class Meta:
        ordering = ["user"]
        verbose_name = _("Wish List")
        verbose_name_plural = _("Wish Lists")

    def __str__(self) -> str:
        return f"{self.user.username}'s Wish List"

    def get_absolute_url(self) -> str:
        return reverse("wish-list:detail")


class WishListItem(models.Model):
    class Status(models.TextChoices):
        WANTED = "WANTED", _("Wanted")
        FOUND = "FOUND", _("Found")
        ACQUIRED = "ACQUIRED", _("Acquired")

    wish_list = models.ForeignKey(
        WishList,
        on_delete=models.CASCADE,
        related_name="wish_list_items",
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name="wish_list_items",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.WANTED,
    )
    priority = models.PositiveSmallIntegerField(
        default=3,
        choices=[(i, str(i)) for i in range(1, 6)],
    )
    desired_grade = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        choices=GRADE_CHOICES,
    )
    max_price = MoneyField(
        _("Maximum Price"),
        max_digits=7,
        decimal_places=2,
        blank=True,
        null=True,
    )
    notes = models.TextField(blank=True)
    added_on = models.DateTimeField(db_default=Now())
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["priority", "issue__series__sort_name", "issue__cover_date"]
        unique_together = [["wish_list", "issue"]]
        indexes = [
            models.Index(fields=["wish_list", "status"], name="wish_list_status_idx"),
            models.Index(fields=["wish_list", "priority"], name="wish_list_priority_idx"),
        ]
        verbose_name = _("Wish List Item")
        verbose_name_plural = _("Wish List Items")

    def __str__(self) -> str:
        return f"{self.wish_list.user.username}: {self.issue} ({self.get_status_display()})"

    def get_absolute_url(self) -> str:
        return reverse("wish-list:detail")
