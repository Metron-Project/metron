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

    #: (content_type_id, object_id) as last loaded or saved, so the post_save
    #: signal can bump the old parent when an attribution is reassigned.
    #: None for an unsaved instance, or one loaded with either field deferred.
    loaded_parent: tuple[int, int] | None = None

    class Meta:
        indexes = [models.Index(fields=["content_type", "object_id"], name="ct_obj_id_idx")]
        ordering = ["content_type", "object_id", "id"]

    def __str__(self) -> str:
        return f"{self.source} Attribution"

    @classmethod
    def from_db(cls, db, field_names, values, *, fetch_mode=None):
        instance = super().from_db(db, field_names, values, fetch_mode=fetch_mode)
        if "content_type_id" in instance.__dict__ and "object_id" in instance.__dict__:
            instance.loaded_parent = (instance.content_type_id, instance.object_id)
        return instance
