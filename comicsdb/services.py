"""Issue editing operations: copying credits from the previous issue and syncing
characters, teams and stories from reprinted issues.

Precondition checks raise or return the user-facing message for the view to show.
"""

import logging
from dataclasses import dataclass, field

from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils.translation import gettext as _

from comicsdb.models import Credits, Issue, Role
from comicsdb.models.series import SeriesType

LOGGER = logging.getLogger(__name__)


# Publishers whose credits must not be copied between issues.
CREDIT_DUPLICATION_EXCLUDED_PUBLISHERS = ("DC Comics", "Marvel")


class CreditDuplicationBlockedError(Exception):
    """Credits can't be duplicated onto an issue; carries the user-facing message."""

    def __init__(self, level: int, message: str):
        super().__init__(message)
        self.level = level
        self.message = message


def credit_duplication_source(issue: Issue) -> tuple[Issue, list[Credits]]:
    """Return the previous issue in the series and the credits to copy from it.

    Raises:
        CreditDuplicationBlockedError: if the publisher is excluded, ``issue``
            already has credits, there is no previous issue, or it has no credits.
    """
    publisher = issue.series.publisher.name
    if publisher in CREDIT_DUPLICATION_EXCLUDED_PUBLISHERS:
        raise CreditDuplicationBlockedError(
            messages.ERROR,
            _("Credit duplication is not allowed for %(publisher)s issues.")
            % {"publisher": publisher},
        )

    if issue.credits_set.exists():
        raise CreditDuplicationBlockedError(
            messages.INFO,
            _(
                "%(issue)s already has credits assigned. "
                "Duplicate operation cancelled to preserve existing data."
            )
            % {"issue": issue},
        )

    try:
        previous_issue = issue.get_previous_by_cover_date(series=issue.series)
    except ObjectDoesNotExist:
        raise CreditDuplicationBlockedError(
            messages.WARNING, _("No previous issue found for %(issue)s.") % {"issue": issue}
        ) from None

    previous_credits = list(
        Credits.objects.filter(issue=previous_issue)
        .select_related("creator")
        .prefetch_related("role")
    )
    if not previous_credits:
        raise CreditDuplicationBlockedError(
            messages.INFO,
            _("No credits found in %(issue)s to duplicate.") % {"issue": previous_issue},
        )
    return previous_issue, previous_credits


def split_variant_cover_credits(source_credits: list[Credits], issue: Issue):
    """Split ``source_credits`` into ``(to_copy, skipped)``.

    A credit whose only role is "Cover" is most likely for a variant cover, so
    it's skipped rather than copied.
    """
    try:
        cover_role = Role.objects.get(name="Cover")
    except Role.DoesNotExist:
        return source_credits, []

    to_copy, skipped = [], []
    for credit in source_credits:
        roles = list(credit.role.all())
        if roles == [cover_role]:
            skipped.append(credit)
            LOGGER.info(
                "Skipping possible variant cover credit for '%s' when duplicating to %s",
                credit.creator,
                issue,
            )
        else:
            to_copy.append(credit)
    return to_copy, skipped


def copy_credits(issue: Issue, source_credits: list[Credits], user) -> None:
    """Copy ``source_credits`` (creator and roles) onto ``issue`` and record ``user`` as editor.

    Uses bulk inserts, which skip the per-credit cache signals; the final
    ``issue.save()`` updates the issue's ``modified`` and bumps the issue cache
    version itself, which is everything those signals would have done.
    """
    through = Credits.role.through
    with transaction.atomic():
        new_credits = Credits.objects.bulk_create(
            Credits(issue=issue, creator=credit.creator) for credit in source_credits
        )
        through.objects.bulk_create(
            through(credits=new_credit, role=role)
            for new_credit, credit in zip(new_credits, source_credits, strict=True)
            for role in credit.role.all()
        )
        issue.edited_by = user
        issue.save(update_fields=["edited_by", "modified"])


# Collected editions: reprint sync applies to them, credit duplication doesn't.
COLLECTED_EDITION_SERIES_TYPES = (
    SeriesType.TRADE_PAPERBACK,
    SeriesType.OMNIBUS,
    SeriesType.HARDCOVER,
)


def supports_reprint_sync(issue: Issue) -> bool:
    """Whether the "sync from reprints" tool applies to ``issue`` (a collected edition)."""
    return issue.series.series_type_id in COLLECTED_EDITION_SERIES_TYPES


def supports_credit_duplication(issue: Issue) -> bool:
    """Whether to offer "duplicate credits": not a collected edition or excluded publisher."""
    return (
        issue.series.series_type_id not in COLLECTED_EDITION_SERIES_TYPES
        and issue.series.publisher.name not in CREDIT_DUPLICATION_EXCLUDED_PUBLISHERS
    )


@dataclass
class ReprintContent:
    """Characters, teams and story titles gathered from an issue's reprints."""

    characters: set = field(default_factory=set)
    teams: set = field(default_factory=set)
    stories: list[str] = field(default_factory=list)
    skipped_reprints: list[str] = field(default_factory=list)


def reprint_sync_blocker(issue: Issue) -> tuple[int, str] | None:
    """Return ``(message_level, message)`` if ``issue`` can't be synced, else ``None``."""
    if not supports_reprint_sync(issue):
        names = dict(
            SeriesType.objects.filter(pk__in=COLLECTED_EDITION_SERIES_TYPES).values_list(
                "pk", "name"
            )
        )
        types = [names[pk] for pk in COLLECTED_EDITION_SERIES_TYPES]
        type_list = f"{', '.join(types[:-1])} and {types[-1]}"
        return messages.ERROR, _(
            "This function only works for %(types)s series types. "
            "This issue is of type '%(current_type)s'."
        ) % {"types": type_list, "current_type": issue.series.series_type.name}

    if not issue.reprints.exists():
        return messages.WARNING, _("No reprinted issues found for %(issue)s.") % {"issue": issue}

    if issue.characters.exists() or issue.teams.exists() or issue.name:
        return messages.INFO, _(
            "%(issue)s already has characters, teams, or stories assigned. "
            "Sync operation cancelled to preserve existing data."
        ) % {"issue": issue}

    return None


def collect_reprint_content(issue: Issue) -> ReprintContent:
    """Gather characters, teams and story titles from ``issue``'s reprints.

    Reprints with more than one story title are skipped. A reprint with no story
    title contributes "[Untitled]".
    """
    content = ReprintContent()
    for reprint in issue.reprints.all():
        if reprint.name and len(reprint.name) > 1:
            content.skipped_reprints.append(str(reprint))
            continue
        content.characters.update(reprint.characters.all())
        content.teams.update(reprint.teams.all())
        content.stories.append(reprint.name[0] if reprint.name else "[Untitled]")
    return content


def apply_reprint_content(issue: Issue, content: ReprintContent, user) -> None:
    """Add ``content`` to ``issue`` and record ``user`` as its editor."""
    with transaction.atomic():
        if content.characters:
            issue.characters.add(*content.characters)
            LOGGER.info(
                "Added %d characters to %s from reprints by %s",
                len(content.characters),
                issue,
                user,
            )

        if content.teams:
            issue.teams.add(*content.teams)
            LOGGER.info("Added %d teams to %s from reprints by %s", len(content.teams), issue, user)

        if content.stories:
            issue.name = content.stories
            LOGGER.info(
                "Added %d story title(s) to %s from reprints by %s",
                len(content.stories),
                issue,
                user,
            )

        issue.edited_by = user
        issue.save(update_fields=["edited_by", "modified", "name"])
