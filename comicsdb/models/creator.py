from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.signals import pre_save
from django.urls import reverse
from sorl.thumbnail import ImageField

from users.models import CustomUser

from .attribution import Attribution
from .common import CommonInfo, pre_save_slug


class Creator(CommonInfo):
    birth = models.DateField("Date of Birth", null=True, blank=True)
    death = models.DateField("Date of Death", null=True, blank=True)
    image = ImageField(upload_to="creator/%Y/%m/%d/", blank=True)
    alias = ArrayField(models.CharField(max_length=100), null=True, blank=True)
    attribution = GenericRelation(Attribution, related_query_name="creators")
    edited_by = models.ForeignKey(CustomUser, default=1, on_delete=models.SET_DEFAULT)

    @property
    def issue_count(self):
        return self.credits_set.all().count()

    @property
    def recent_issues(self):
        return self.credits_set.order_by("-issue__cover_date").all()[:5]

    @property
    def wikipedia(self):
        return self.attribution.filter(source=Attribution.Source.WIKIPEDIA)

    @property
    def marvel(self):
        return self.attribution.filter(source=Attribution.Source.MARVEL)

    def get_absolute_url(self):
        return reverse("creator:detail", args=[self.slug])

    def __str__(self) -> str:
        return self.name


pre_save.connect(pre_save_slug, sender=Creator, dispatch_uid="pre_save_creator")
