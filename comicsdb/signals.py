import logging

from django.utils import timezone
from sorl.thumbnail import delete

LOGGER = logging.getLogger(__name__)


def pre_delete_image(sender, instance, **kwargs):
    if instance.image:
        delete(instance.image)


def pre_delete_credit(sender, instance, **kwargs):
    LOGGER.info("Deleting %s credit for %s", instance.creator, instance.issue)


def update_series_modified_on_issue_save(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415
    from comicsdb.models import Series  # noqa: PLC0415

    Series.objects.filter(pk=instance.series_id).update(modified=timezone.now())
    bump_model_version(ModelLabel.ISSUE)
    bump_model_version(ModelLabel.SERIES)


def update_series_modified_on_issue_delete(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415
    from comicsdb.models import Series  # noqa: PLC0415

    Series.objects.filter(pk=instance.series_id).update(modified=timezone.now())
    bump_model_version(ModelLabel.ISSUE)
    bump_model_version(ModelLabel.SERIES)


def update_related_modified(parent_model, instance, action, pk_set):
    """Shared logic for M2M post_add/post_remove/post_clear on Arc, Character, Team."""
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    from comicsdb.models import Issue  # noqa: PLC0415

    if isinstance(instance, Issue):
        # pk_set is None for post_clear; skip since affected parents are unknown
        if pk_set:
            parent_model.objects.filter(pk__in=pk_set).update(modified=timezone.now())
    else:
        # instance is the parent (e.g. arc.issues.add/clear(...))
        parent_model.objects.filter(pk=instance.pk).update(modified=timezone.now())


def update_arc_modified(sender, instance, action, pk_set, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415
    from comicsdb.models import Arc  # noqa: PLC0415

    update_related_modified(Arc, instance, action, pk_set)
    if action in ("post_add", "post_remove", "post_clear"):
        bump_model_version(ModelLabel.ARC)


def update_character_modified(sender, instance, action, pk_set, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415
    from comicsdb.models import Character  # noqa: PLC0415

    update_related_modified(Character, instance, action, pk_set)
    if action in ("post_add", "post_remove", "post_clear"):
        bump_model_version(ModelLabel.CHARACTER)


def update_team_modified(sender, instance, action, pk_set, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415
    from comicsdb.models import Team  # noqa: PLC0415

    update_related_modified(Team, instance, action, pk_set)
    if action in ("post_add", "post_remove", "post_clear"):
        bump_model_version(ModelLabel.TEAM)


def update_issue_modified_on_credit_change(sender, instance, **kwargs):
    """Credits changes aren't reflected on the parent Issue's `modified` by
    default; bump it explicitly so the issue's cached detail response
    (which embeds credits) invalidates."""
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415
    from comicsdb.models import Issue  # noqa: PLC0415

    Issue.objects.filter(pk=instance.issue_id).update(modified=timezone.now())
    bump_model_version(ModelLabel.ISSUE)


def bump_arc_cache(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415

    bump_model_version(ModelLabel.ARC)


def bump_character_cache(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415

    bump_model_version(ModelLabel.CHARACTER)


def bump_creator_cache(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415

    bump_model_version(ModelLabel.CREATOR)


def bump_imprint_cache(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415

    bump_model_version(ModelLabel.IMPRINT)


def bump_publisher_cache(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415

    bump_model_version(ModelLabel.PUBLISHER)


def bump_series_cache(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415

    bump_model_version(ModelLabel.SERIES)


def bump_team_cache(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415

    bump_model_version(ModelLabel.TEAM)


def bump_universe_cache(sender, instance, **kwargs):
    from api.cache import ModelLabel, bump_model_version  # noqa: PLC0415

    bump_model_version(ModelLabel.UNIVERSE)
