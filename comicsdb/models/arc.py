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
from users.models import CustomUser

LOGGER = logging.getLogger(__name__)


class Arc(CommonInfo):
    image = ImageField(upload_to="arc/%Y/%m/%d/", blank=True)
    attribution = GenericRelation(Attribution, related_query_name="arcs")
    created_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="arcs_created"
    )
    edited_by = models.ForeignKey(
        CustomUser, default=1, on_delete=models.SET_DEFAULT, related_name="arcs_edited"
    )
    history = HistoricalRecords()

    def save(self, *args, **kwargs) -> None:
        # Let's delete the original image if we're replacing it by uploading a new one.
        with contextlib.suppress(ObjectDoesNotExist):
            this = Arc.objects.get(id=self.id)
            if this.image and this.image != self.image:
                if self.image:
                    LOGGER.info("Replacing '%s' with '%s'", this.image, self.image)
                else:
                    LOGGER.info("Replacing '%s' with 'None'.", this.image)
                this.image.delete(save=False)
        return super().save(*args, **kwargs)

    @property
    def issue_count(self) -> int:
        return self.issues.count()

    def get_absolute_url(self):
        return reverse("arc:detail", args=[self.slug])

    def __str__(self) -> str:
        return self.name

    class Meta:
        indexes = [
            models.Index(fields=["name"], name="arc_name_idx"),
            models.Index(fields=["cv_id"], name="arc_cv_id_idx"),
            models.Index(fields=["gcd_id"], name="arc_gcd_id_idx"),
        ]
        ordering = ["name"]


pre_save.connect(pre_save_slug, sender=Arc, dispatch_uid="pre_save_arc")
