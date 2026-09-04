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
    """Shared logic for M2M post_add/post_remove/post_clear on Arc, Character, Team.

    Bumps both sides of the relationship's `modified`: the parent (Arc/
    Character/Team -- for its own issue_list cache) and the specific
    Issue(s) involved (for that issue's own cached detail response, which
    embeds this relationship). Both updates are scoped by pk/pk_set to the
    objects actually affected -- never a blanket update -- so this doesn't
    reintroduce the cross-contamination that ModelLabel.ISSUE/SERIES had as
    global version counters.
    """
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    from comicsdb.models import Issue  # noqa: PLC0415

    now = timezone.now()
    if isinstance(instance, Issue):
        # issue.arcs.add(...)/.remove()/.clear() -- instance is the Issue.
        Issue.objects.filter(pk=instance.pk).update(modified=now)
        # pk_set is None for post_clear; skip since affected parents are unknown
        if pk_set:
            parent_model.objects.filter(pk__in=pk_set).update(modified=now)
    else:
        # instance is the parent (e.g. arc.issues.add/clear(...))
        parent_model.objects.filter(pk=instance.pk).update(modified=now)
        if pk_set:
            Issue.objects.filter(pk__in=pk_set).update(modified=now)


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


def update_issue_modified_on_universe_change(sender, instance, action, pk_set, **kwargs):
    """Issue.universes is a M2M, but -- unlike arcs/characters/teams --
    Universe has no issue_list-style action needing its own side bumped,
    so only the Issue side needs updating here for the issue's cached
    detail response (which embeds `universes`) to invalidate. The ISSUE
    cache version is also bumped since IssueListSerializer embeds
    `modified`, and that field just changed for this issue."""
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    from comicsdb.models import Issue  # noqa: PLC0415

    now = timezone.now()
    if isinstance(instance, Issue):
        Issue.objects.filter(pk=instance.pk).update(modified=now)
    elif pk_set:
        Issue.objects.filter(pk__in=pk_set).update(modified=now)
    bump_model_version(ModelLabel.ISSUE)


def update_issue_modified_on_reprint_change(sender, instance, action, pk_set, **kwargs):
    """Issue.reprints is a symmetric self-referential M2M -- both sides of
    a reprints.add()/.remove() are Issue instances, so bump both the issue
    the change was made through and the affected issue(s) on the other
    side; both cached detail responses embed `reprints`. The ISSUE cache
    version is also bumped since IssueListSerializer embeds `modified`."""
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    from comicsdb.models import Issue  # noqa: PLC0415

    now = timezone.now()
    Issue.objects.filter(pk=instance.pk).update(modified=now)
    if pk_set:
        Issue.objects.filter(pk__in=pk_set).update(modified=now)
    bump_model_version(ModelLabel.ISSUE)


def update_issue_modified_on_variant_change(sender, instance, **kwargs):
    """Variant changes aren't reflected on the parent Issue's `modified` by
    default; bump it explicitly so the issue's cached detail response
    (which embeds variants) invalidates. The ISSUE cache version is also
    bumped since IssueListSerializer embeds `modified`."""
    from comicsdb.models import Issue  # noqa: PLC0415

    Issue.objects.filter(pk=instance.issue_id).update(modified=timezone.now())
    bump_model_version(ModelLabel.ISSUE)


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


def bump_owner_modified_on_m2m_change(owner_model, cache_label, instance, action, pk_set):
    """Shared logic for m2m_changed signals on a plain (non-Issue) m2m field
    where only the owning side's own cached response embeds the relation --
    Character.creators/teams/universes, Team.creators/universes,
    Series.genres. Bumps the owner's `modified` (self-invalidates its
    detail cache, which embeds the relation) and its cache version (its
    list response also embeds `modified`, which just changed).
    """
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    now = timezone.now()
    if isinstance(instance, owner_model):
        # e.g. character.creators.add(...) -- instance is the owner.
        owner_model.objects.filter(pk=instance.pk).update(modified=now)
        bump_model_version(cache_label)
    elif pk_set:
        # e.g. creator.characters.add(...) -- instance is the related
        # object; pk_set holds the affected owner pk(s). pk_set is None
        # for post_clear from this side, so skip (affected owners unknown).
        owner_model.objects.filter(pk__in=pk_set).update(modified=now)
        bump_model_version(cache_label)


def update_character_modified_on_creator_change(sender, instance, action, pk_set, **kwargs):
    from comicsdb.models import Character  # noqa: PLC0415

    bump_owner_modified_on_m2m_change(Character, ModelLabel.CHARACTER, instance, action, pk_set)


def update_character_modified_on_team_change(sender, instance, action, pk_set, **kwargs):
    from comicsdb.models import Character  # noqa: PLC0415

    bump_owner_modified_on_m2m_change(Character, ModelLabel.CHARACTER, instance, action, pk_set)


def update_character_modified_on_universe_change(sender, instance, action, pk_set, **kwargs):
    from comicsdb.models import Character  # noqa: PLC0415

    bump_owner_modified_on_m2m_change(Character, ModelLabel.CHARACTER, instance, action, pk_set)


def update_team_modified_on_creator_change(sender, instance, action, pk_set, **kwargs):
    from comicsdb.models import Team  # noqa: PLC0415

    bump_owner_modified_on_m2m_change(Team, ModelLabel.TEAM, instance, action, pk_set)


def update_team_modified_on_universe_change(sender, instance, action, pk_set, **kwargs):
    from comicsdb.models import Team  # noqa: PLC0415

    bump_owner_modified_on_m2m_change(Team, ModelLabel.TEAM, instance, action, pk_set)


def update_series_modified_on_genre_change(sender, instance, action, pk_set, **kwargs):
    from comicsdb.models import Series  # noqa: PLC0415

    bump_owner_modified_on_m2m_change(Series, ModelLabel.SERIES, instance, action, pk_set)


def update_series_modified_on_associated_change(sender, instance, action, pk_set, **kwargs):
    """Series.associated is a self-referential m2m -- both sides of an
    associated.add()/.remove() are Series instances (like Issue.reprints),
    so bump both the series the change was made through and the affected
    series on the other side; both cached detail responses embed
    `associated`."""
    if action not in ("post_add", "post_remove", "post_clear"):
        return

    from comicsdb.models import Series  # noqa: PLC0415

    now = timezone.now()
    Series.objects.filter(pk=instance.pk).update(modified=now)
    bump_model_version(ModelLabel.SERIES)
    if pk_set:
        Series.objects.filter(pk__in=pk_set).update(modified=now)


def bump_cache(label, sender, instance, **kwargs):
    """Generic post_save/post_delete receiver for the models whose cache
    invalidation is *only* "bump my own version counter" -- Arc, Character,
    Creator, Imprint, Publisher, Series, Team, Universe. Wired up via
    functools.partial(bump_cache, label) in comicsdb/apps.py so one
    function covers all eight instead of eight near-identical wrappers."""
    bump_model_version(label)
