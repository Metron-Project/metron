from django.db import models
from django.utils.translation import gettext_lazy as _

from comicsdb.models.creator import Creator
from comicsdb.models.issue import Issue


class Role(models.Model):
    name = models.CharField(max_length=25)
    order = models.PositiveSmallIntegerField(unique=True)
    notes = models.TextField(blank=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name


class Credits(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    creator = models.ForeignKey(Creator, on_delete=models.CASCADE)
    role = models.ManyToManyField(Role)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["issue", "creator"], name="issue_creator_idx")]
        ordering = ["issue", "creator__name"]
        unique_together = ["issue", "creator"]
        verbose_name_plural = _("Credits")

    def __str__(self) -> str:
        return f"{self.issue}: {self.creator}"
