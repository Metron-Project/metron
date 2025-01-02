import itertools

from django.db import models
from django.db.models.functions import Now
from django.utils.text import slugify


def generate_slug_from_name(instance):
    slug_candidate = slug_original = (
        slugify(f"{instance.name}-slug") if instance.name.isdigit() else slugify(instance.name)
    )
    klass = instance.__class__
    for i in itertools.count(1):
        if not klass.objects.filter(slug=slug_candidate).exists():
            break
        slug_candidate = f"{slug_original}-{i}"

    return slug_candidate


def pre_save_slug(sender, instance, **kwargs):
    if not instance.slug:
        instance.slug = generate_slug_from_name(instance)


class CommonInfo(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    desc = models.TextField("Description", blank=True)
    cv_id = models.PositiveIntegerField("Comic Vine ID", null=True, blank=True, unique=True)
    gcd_id = models.PositiveIntegerField("GCD ID", null=True, blank=True, unique=True)
    modified = models.DateTimeField(auto_now=True)
    created_on = models.DateTimeField(db_default=Now())

    class Meta:
        abstract = True
