from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class Attribution(models.Model):
    class Source(models.TextChoices):
        MARVEL = "M", _("Marvel")
        WIKIPEDIA = "W", _("Wikipedia")
        GCD = "G", _("Grand Comics Database")
        DC = "D", _("DC")

    source = models.CharField(max_length=1, choices=Source.choices, default=Source.WIKIPEDIA)
    url = models.URLField()

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"], name="ct_obj_id_idx")]
        ordering = ["content_type", "object_id"]

    def __str__(self) -> str:
        return f"{self.source} Attribution"
