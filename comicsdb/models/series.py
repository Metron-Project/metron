import itertools

from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.text import slugify
from simple_history.models import HistoricalRecords

from comicsdb.models.attribution import Attribution
from comicsdb.models.common import CommonInfo
from comicsdb.models.genre import Genre
from comicsdb.models.imprint import Imprint
from comicsdb.models.publisher import Publisher
from users.models import CustomUser


class SeriesType(models.Model):
    name = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Series(CommonInfo):
    class Status(models.IntegerChoices):
        CANCELLED = 1
        COMPLETED = 2
        HIATUS = 3
        ONGOING = 4

    sort_name = models.CharField(max_length=255)
    volume = models.PositiveSmallIntegerField("Volume Number")
    year_began = models.PositiveSmallIntegerField("Year Began")
    year_end = models.PositiveSmallIntegerField("Year Ended", null=True, blank=True)
    series_type = models.ForeignKey(SeriesType, on_delete=models.CASCADE)
    status = models.IntegerField(choices=Status.choices, default=Status.ONGOING)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name="series")
    imprint = models.ForeignKey(
        Imprint, on_delete=models.SET_NULL, null=True, blank=True, related_name="series"
    )
    collection = models.BooleanField(
        "Allow Collection Title",
        db_default=False,
        help_text="Whether a series has a collection title. "
        "Normally this only applies to Trade Paperbacks.",
    )
    genres = models.ManyToManyField(Genre, blank=True, related_name="series")
    associated = models.ManyToManyField("self", blank=True)
    attribution = GenericRelation(Attribution, related_query_name="series")
    created_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="series_created"
    )
    edited_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="series_edited"
    )
    history = HistoricalRecords(m2m_fields=[genres, associated])

    def get_absolute_url(self):
        return reverse("series:detail", args=[self.slug])

    def __str__(self) -> str:
        match self.series_type.id:
            case 12:
                return f"{self.name} ({self.year_began}) Digital"
            case 10:
                return f"{self.name} TPB ({self.year_began})"
            case 8:
                return f"{self.name} HC ({self.year_began})"
            case 9:
                return f"{self.name} GN ({self.year_began})"
            case _:
                return f"{self.name} ({self.year_began})"

    def first_issue_cover(self):
        try:
            return self.issues.all().first().image
        except AttributeError:
            return None

    @property
    def issue_count(self) -> int:
        return self.issues.all().count()

    class Meta:
        indexes = [
            models.Index(fields=["sort_name", "year_began"], name="sort_year_began_idx"),
            models.Index(fields=["name"], name="series_name_idx"),
        ]
        ordering = ["sort_name", "year_began"]
        unique_together = ["publisher", "name", "volume", "series_type"]
        verbose_name_plural = "Series"


def generate_series_slug(instance):
    slug_candidate = slug_original = slugify(f"{instance.name}-{instance.year_began}")
    klass = instance.__class__
    for i in itertools.count(1):
        if not klass.objects.filter(slug=slug_candidate).exists():
            break
        slug_candidate = f"{slug_original}-{i}"

    return slug_candidate


def pre_save_series_slug(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = generate_series_slug(instance)


pre_save.connect(pre_save_series_slug, sender=Series, dispatch_uid="pre_save_series")
