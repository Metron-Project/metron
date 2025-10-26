from django.db import models
from simple_history.models import HistoricalRecords


class Genre(models.Model):
    name = models.CharField(max_length=25)
    desc = models.TextField("Description", blank=True)
    modified = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
