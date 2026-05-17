from django.db import models
from django.db.models.functions import Now
from django.urls import reverse

from comicsdb.models.series import Series
from users.models import CustomUser


class PullList(models.Model):
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="pull_list",
    )
    is_private = models.BooleanField(default=False)
    series = models.ManyToManyField(
        Series,
        through="PullListSeries",
        related_name="in_pull_lists",
        blank=True,
    )
    modified = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(db_default=Now())

    class Meta:
        verbose_name = "Pull List"
        verbose_name_plural = "Pull Lists"

    def __str__(self) -> str:
        return f"{self.user.username}'s Pull List"

    def get_absolute_url(self) -> str:
        return reverse("pull-list:detail")


class PullListSeries(models.Model):
    pull_list = models.ForeignKey(
        PullList,
        on_delete=models.CASCADE,
        related_name="pull_list_series",
    )
    series = models.ForeignKey(
        Series,
        on_delete=models.CASCADE,
        related_name="pull_list_series",
    )
    added_on = models.DateTimeField(db_default=Now())

    class Meta:
        ordering = ["series__sort_name"]
        unique_together = [["pull_list", "series"]]
        indexes = [
            models.Index(fields=["pull_list", "series"], name="pull_list_series_idx"),
        ]
        verbose_name = "Pull List Series"
        verbose_name_plural = "Pull List Series"

    def __str__(self) -> str:
        return f"{self.pull_list} — {self.series}"
