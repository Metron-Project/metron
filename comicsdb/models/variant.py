import contextlib
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from djmoney.models.fields import MoneyField
from sorl.thumbnail import ImageField

from comicsdb.models.issue import Issue

LOGGER = logging.getLogger(__name__)


class Variant(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="variants")
    image = ImageField("Variant Cover", upload_to="variants/%Y/%m/%d/")
    name = models.CharField("Name", max_length=255, blank=True)
    price = MoneyField("Price", max_digits=5, decimal_places=2, blank=True, null=True)
    sku = models.CharField("Distributor SKU", max_length=12, blank=True)
    upc = models.CharField("UPC Code", max_length=20, blank=True)

    class Meta:
        indexes = [models.Index(fields=["issue"], name="issue_idx")]
        ordering = ["issue"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        # Let's delete the original image if we're replacing it by uploading a new one.
        with contextlib.suppress(ObjectDoesNotExist):
            this = Variant.objects.get(id=self.id)
            if this.image and this.image != self.image:
                if self.image:
                    LOGGER.info("Replacing '%s' with '%s'", this.image, self.image)
                else:
                    LOGGER.info("Replacing '%s' with 'None'.", this.image)
                this.image.delete(save=False)
        return super().save(*args, **kwargs)
