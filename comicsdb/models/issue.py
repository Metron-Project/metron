import contextlib
import itertools
import logging
from datetime import date

import imagehash
from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import pre_save
from django.urls import reverse
from django.utils.text import slugify
from djmoney.models.fields import MoneyField
from PIL import Image
from sorl.thumbnail import ImageField

from comicsdb.models.arc import Arc
from comicsdb.models.attribution import Attribution
from comicsdb.models.character import Character
from comicsdb.models.common import CommonInfo
from comicsdb.models.creator import Creator
from comicsdb.models.rating import Rating
from comicsdb.models.series import Series
from comicsdb.models.team import Team
from comicsdb.models.universe import Universe
from users.models import CustomUser

LOGGER = logging.getLogger(__name__)


class GraphicNovelManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(series__series_type__name="Graphic Novel")


class TradePaperbackManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(series__series_type__name="Trade Paperback")


class Issue(CommonInfo):
    series = models.ForeignKey(Series, on_delete=models.CASCADE, related_name="issues")
    name = ArrayField(models.CharField("Story Title", max_length=150), blank=True, default=list)
    title = models.CharField("Collection Title", max_length=255, blank=True)
    number = models.CharField(max_length=25)
    alt_number = models.CharField("Alternative Number", max_length=25, blank=True)
    cover_date = models.DateField("Cover Date")
    store_date = models.DateField("In Store Date", null=True, blank=True)
    foc_date = models.DateField("Final Order Cutoff Date", null=True, blank=True)
    price = MoneyField("Cover Price", max_digits=5, decimal_places=2, blank=True, null=True)
    rating = models.ForeignKey(Rating, default=1, on_delete=models.SET_DEFAULT)
    sku = models.CharField("Distributor SKU", max_length=12, blank=True)
    isbn = models.CharField("ISBN", max_length=13, blank=True)
    upc = models.CharField("UPC Code", max_length=20, blank=True)
    page = models.PositiveSmallIntegerField("Page Count", null=True, blank=True)
    image = ImageField("Cover", upload_to="issue/%Y/%m/%d/", blank=True)
    cover_hash = models.CharField("Cover Hash", max_length=16, blank=True)
    arcs = models.ManyToManyField(Arc, blank=True, related_name="issues")
    creators = models.ManyToManyField(Creator, through="Credits", blank=True, related_name="issues")
    characters = models.ManyToManyField(Character, blank=True, related_name="issues")
    teams = models.ManyToManyField(Team, blank=True, related_name="issues")
    universes = models.ManyToManyField(Universe, blank=True, related_name="issues")
    reprints = models.ManyToManyField("self", blank=True)
    attribution = GenericRelation(Attribution, related_query_name="issues")
    created_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="issues_created"
    )
    edited_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="issues_edited"
    )

    objects = models.Manager()
    graphic_novels = GraphicNovelManager()
    tpb = TradePaperbackManager()

    def get_absolute_url(self):
        return reverse("issue:detail", args=[self.slug])

    @property
    def wikipedia(self):
        return self.attribution.filter(source=Attribution.Source.WIKIPEDIA)

    @property
    def marvel(self):
        return self.attribution.filter(source=Attribution.Source.MARVEL)

    @property
    def is_foc_past_due(self):
        return date.today() > self.foc_date

    def save(self, *args, **kwargs) -> None:
        # Let's delete the original image if we're replacing it by uploading a new one.
        with contextlib.suppress(ObjectDoesNotExist):
            this: Issue = Issue.objects.get(id=self.id)
            if this.image and this.image != self.image:
                if self.image:
                    LOGGER.info("Replacing '%s' with '%s'", this.image, self.image)
                else:
                    LOGGER.info("Replacing '%s' with 'None'.", this.image)
                this.image.delete(save=False)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        match self.series.series_type.id:
            case 12:
                return f"{self.series} Chapter #{self.number}"
            case _:
                return f"{self.series} #{self.number}"

    class Meta:
        indexes = [
            models.Index(
                fields=["series", "cover_date", "store_date", "number"],
                name="series_cover_store_num_idx",
            ),
            models.Index(fields=["series", "number"], name="series_number_idx"),
        ]
        ordering = ["series__sort_name", "cover_date", "store_date", "number"]
        unique_together = ["series", "number"]


def generate_issue_slug(instance: Issue):
    slug_candidate = slug_original = slugify(f"{instance.series.slug}-{instance.number}")
    for i in itertools.count(1):
        if not Issue.objects.filter(slug=slug_candidate).exists():
            break
        slug_candidate = f"{slug_original}-{i}"

    return slug_candidate


def pre_save_issue_slug(sender, instance: Issue, *args, **kwargs) -> None:
    if not instance.slug:
        instance.slug = generate_issue_slug(instance)


def generate_cover_hash(instance: Issue) -> str:
    with Image.open(instance.image) as img:
        try:
            cover_hash = str(imagehash.phash(img))
        except OSError as e:
            cover_hash = ""
            LOGGER.error("Unable to generate cover hash for '%s': %s", instance, e)
    return cover_hash


def pre_save_cover_hash(sender, instance: Issue, *args, **kwargs) -> None:
    if instance.image:
        ch = generate_cover_hash(instance)
        if instance.cover_hash != ch:
            LOGGER.info(
                "Updating cover hash from '%s' to '%s' for %s",
                instance.cover_hash,
                ch,
                instance,
            )
            instance.cover_hash = ch
        return

    if instance.cover_hash:
        LOGGER.info("Updating cover hash from '%s' to '' for %s", instance.cover_hash, instance)
        instance.cover_hash = ""
        return


pre_save.connect(pre_save_issue_slug, sender=Issue)
pre_save.connect(pre_save_cover_hash, sender=Issue)
