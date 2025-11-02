import itertools

from django.db import models
from django.db.models.functions import Now
from django.utils.text import slugify


def generate_slug_from_name(instance):
    base_slug = (
        slugify(f"{instance.name}-slug") if instance.name.isdigit() else slugify(instance.name)
    )
    klass = instance.__class__

    # Fetch all matching slugs at once to avoid multiple database queries
    existing_slugs = set(
        klass.objects.filter(slug__startswith=base_slug).values_list("slug", flat=True)
    )

    if base_slug not in existing_slugs:
        return base_slug

    for i in itertools.count(1):
        slug_candidate = f"{base_slug}-{i}"
        if slug_candidate not in existing_slugs:
            return slug_candidate

    # This should never be reached due to itertools.count() being infinite
    return base_slug  # pragma: no cover


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
