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


class Imprint(CommonInfo):
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE, related_name="imprints")
    founded = models.PositiveSmallIntegerField("Year Founded", null=True, blank=True)
    image = ImageField("Logo", upload_to="imprint/%Y/%m/%d", null=True, blank=True)
    attribution = GenericRelation(Attribution, related_query_name="imprints")
    created_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="imprints_created"
    )
    edited_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="imprints_edited"
    )
    history = HistoricalRecords()

    def save(self, *args, **kwargs) -> None:
        # Let's delete the original image if we're replacing it by uploading a new one.
        with contextlib.suppress(ObjectDoesNotExist):
            this = Imprint.objects.get(id=self.id)
            if this.image and this.image != self.image:
                if self.image:
                    LOGGER.info("Replacing '%s' with '%s'", this.image, self.image)
                else:
                    LOGGER.info("Replacing '%s' with 'None'.", this.image)
                this.image.delete(save=False)
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("imprint:detail", args=[self.slug])

    @property
    def series_count(self):
        return self.series.all().count()

    @property
    def wikipedia(self):
        return self.attribution.filter(source=Attribution.Source.WIKIPEDIA)

    @property
    def marvel(self):
        return self.attribution.filter(source=Attribution.Source.MARVEL)

    def __str__(self) -> str:
        return self.name

    class Meta:
        indexes = [models.Index(fields=["name"], name="imprint_name_idx")]
        ordering = ["name"]


pre_save.connect(pre_save_slug, sender=Imprint, dispatch_uid="pre_save_imprint")
