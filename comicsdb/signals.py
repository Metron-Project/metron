import logging

from django.utils import timezone
from sorl.thumbnail import delete

from api.cache import ModelLabel, bump_model_version

LOGGER = logging.getLogger(__name__)


def pre_delete_image(sender, instance, **kwargs):
    if instance.image:
        delete(instance.image)


def pre_delete_credit(sender, instance, **kwargs):
    LOGGER.info("Deleting %s credit for %s", instance.creator, instance.issue)


def update_series_modified_on_issue_save(sender, instance, **kwargs):
    from comicsdb.models import Series  # noqa: PLC0415

    Series.objects.filter(pk=instance.series_id).update(modified=timezone.now())
    bump_model_version(ModelLabel.ISSUE)
    bump_model_version(ModelLabel.SERIES)


def update_series_modified_on_issue_delete(sender, instance, **kwargs):
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
    from comicsdb.models import Arc  # noqa: PLC0415

    update_related_modified(Arc, instance, action, pk_set)
    if action in ("post_add", "post_remove", "post_clear"):
        bump_model_version(ModelLabel.ARC)


def update_character_modified(sender, instance, action, pk_set, **kwargs):
    from comicsdb.models import Character  # noqa: PLC0415

    update_related_modified(Character, instance, action, pk_set)
    if action in ("post_add", "post_remove", "post_clear"):
        bump_model_version(ModelLabel.CHARACTER)


def update_team_modified(sender, instance, action, pk_set, **kwargs):
    from comicsdb.models import Team  # noqa: PLC0415

    update_related_modified(Team, instance, action, pk_set)
    if action in ("post_add", "post_remove", "post_clear"):
        bump_model_version(ModelLabel.TEAM)


def update_issue_modified_on_credit_change(sender, instance, **kwargs):
    """Credits changes aren't reflected on the parent Issue's `modified` by
    default; bump it explicitly so the issue's cached detail response
    (which embeds credits) invalidates."""
    from comicsdb.models import Issue  # noqa: PLC0415

    Issue.objects.filter(pk=instance.issue_id).update(modified=timezone.now())
    bump_model_version(ModelLabel.ISSUE)


def update_issue_modified_on_credit_role_change(sender, instance, action, pk_set, **kwargs):
    """Credits.role is a M2M -- .add()/.remove()/.set() don't call
    Credits.save(), so update_issue_modified_on_credit_change (a post_save
    hook) never fires for role-only changes. In particular,
    CreditSerializer.create() calls Credits.objects.create() (bumping
    Issue.modified with an empty role list) and only then calls
    credit.role.add(...): without this second bump, a request landing in
    that window could cache the issue with an empty role list under a
    `modified` key that's never touched again."""
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    from comicsdb.models import Issue  # noqa: PLC0415

    Issue.objects.filter(pk=instance.issue_id).update(modified=timezone.now())
    bump_model_version(ModelLabel.ISSUE)


def _make_cache_bumper(label):
    def bump_cache(sender, instance, **kwargs):
        bump_model_version(label)

    return bump_cache


bump_arc_cache = _make_cache_bumper(ModelLabel.ARC)
bump_character_cache = _make_cache_bumper(ModelLabel.CHARACTER)
bump_creator_cache = _make_cache_bumper(ModelLabel.CREATOR)
bump_imprint_cache = _make_cache_bumper(ModelLabel.IMPRINT)
bump_publisher_cache = _make_cache_bumper(ModelLabel.PUBLISHER)
bump_series_cache = _make_cache_bumper(ModelLabel.SERIES)
bump_team_cache = _make_cache_bumper(ModelLabel.TEAM)
bump_universe_cache = _make_cache_bumper(ModelLabel.UNIVERSE)
