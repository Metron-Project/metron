import contextlib
import logging

from django.contrib.contenttypes.fields import GenericRelation
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import pre_save
from django.urls import reverse
from simple_history.models import HistoricalRecords
from sorl.thumbnail import ImageField

from comicsdb.models.attribution import Attribution
from comicsdb.models.common import CommonInfo, pre_save_slug
from comicsdb.models.publisher import Publisher
from users.models import CustomUser

LOGGER = logging.getLogger(__name__)


class Universe(CommonInfo):
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name="universes")
    image = ImageField(upload_to="universe/%Y/%m/%d/", blank=True)
    designation = models.CharField(max_length=255, blank=True)
    attribution = GenericRelation(Attribution, related_query_name="universes")
    created_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="universes_created"
    )
    edited_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="universes_edited"
    )
    history = HistoricalRecords()

    def save(self, *args, **kwargs) -> None:
        # Let's delete the original image if we're replacing it by uploading a new one.
        with contextlib.suppress(ObjectDoesNotExist):
            this = Universe.objects.get(id=self.id)
            if this.image and this.image != self.image:
                if self.image:
                    LOGGER.info("Replacing '%s' with '%s'", this.image, self.image)
                else:
                    LOGGER.info("Replacing '%s' with 'None'.", this.image)
                this.image.delete(save=False)
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("universe:detail", args=[self.slug])

    @property
    def issue_count(self):
        return self.issues.all().count()

    @property
    def first_appearance(self):
        return self.issues.order_by("cover_date").all().first

    @property
    def wikipedia(self):
        return self.attribution.filter(source=Attribution.Source.WIKIPEDIA)

    @property
    def marvel(self):
        return self.attribution.filter(source=Attribution.Source.MARVEL)

    @property
    def universe_name(self) -> str:
        if self.designation and self.name != self.designation:
            return f"{self.name} — {self.designation}"
        return self.name

    def __str__(self) -> str:
        return self.universe_name

    class Meta:
        indexes = [
            models.Index(fields=["name"], name="universe_name_idx"),
            models.Index(fields=["cv_id"], name="universe_cv_id_idx"),
            models.Index(fields=["gcd_id"], name="universe_gcd_id_idx"),
        ]
        ordering = ["name", "designation"]
        unique_together = ["publisher", "name", "designation"]
        db_table_comment = "Publisher Universes"


pre_save.connect(pre_save_slug, sender=Universe, dispatch_uid="pre_save_universe")
