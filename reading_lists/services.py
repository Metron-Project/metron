"""Reading list permissions, bulk issue adding and detail-page breakdowns."""

from django.db import models
from django.db.models import Count, Prefetch
from django.utils.translation import gettext_lazy as _

from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.credits import ARTIST_ROLE_NAMES, WRITER_ROLE_NAMES, Credits, Role
from reading_lists.models import READING_LIST_EDITOR_GROUP, ReadingListItem

_ISSUE_TYPE_META = {
    "CORE": (_("Core"), "#3273dc"),
    "TIE_IN": (_("Tie-In"), "#f5b400"),
    "PROLOGUE": (_("Prologue"), "#3e8ed0"),
    "EPILOGUE": (_("Epilogue"), "#48c78e"),
}


# Featured creators are the writers and artists; each role is shown as "Writer" or "Artist".
_CREDIT_ROLE_NAMES = (*WRITER_ROLE_NAMES, *ARTIST_ROLE_NAMES)


_CREDIT_ROLE_DISPLAY = {
    **dict.fromkeys(WRITER_ROLE_NAMES, _("Writer")),
    **dict.fromkeys(ARTIST_ROLE_NAMES, _("Artist")),
}


def can_manage_reading_list(user, reading_list):
    """Check if a user can manage (edit/delete) a reading list.

    Users can manage a list if they are:
    - The owner of the list
    - Staff editing a Metron list
    - Member of 'reading list editor' group editing a Metron list
    """
    is_owner = reading_list.user == user

    if reading_list.user.username == "Metron":
        is_staff = user.is_staff
        is_editor_group = user.groups.filter(name=READING_LIST_EDITOR_GROUP).exists()
        return is_owner or is_staff or is_editor_group

    return is_owner


def can_assign_reading_list_to_metron(user):
    """Check if a user can reassign a reading list's owner to the Metron account.

    Allowed for staff or members of the 'reading list editor' group.
    """
    return user.is_staff or user.groups.filter(name=READING_LIST_EDITOR_GROUP).exists()


def add_issues_to_reading_list(reading_list, candidate_issues, position):
    """Add issues not already in the list, ordered at the beginning or end.

    Existing items are shifted down when inserting at the beginning; otherwise
    new issues are appended after the current maximum order. Returns the number
    of issues actually added (issues already in the list are skipped).
    """
    existing_issue_ids = set(reading_list.reading_list_items.values_list("issue_id", flat=True))
    new_issues = [issue for issue in candidate_issues if issue.pk not in existing_issue_ids]

    if not new_issues:
        return 0

    if position == "beginning":
        start_order = 1
        existing_items = reading_list.reading_list_items.order_by("order")
        for idx, item in enumerate(existing_items, start=len(new_issues) + 1):
            if item.order != idx:
                item.order = idx
                item.save()
    else:
        max_order = (
            reading_list.reading_list_items.aggregate(models.Max("order"))["order__max"] or 0
        )
        start_order = max_order + 1

    ReadingListItem.objects.bulk_create(
        ReadingListItem(reading_list=reading_list, issue=issue, order=start_order + idx)
        for idx, issue in enumerate(new_issues)
    )
    return len(new_issues)


def build_reading_list_breakdown_context(reading_list_items):
    """Compute issue-type/series/publisher breakdowns and featured creators/characters.

    ``reading_list_items`` must be a non-empty, pre-fetched sequence of
    ReadingListItem rows (as built by ReadingListDetailView.get_queryset).
    """
    type_counts = {}
    series_counts = {}
    publisher_counts = {}

    for item in reading_list_items:
        key = item.issue_type or ""
        if key:
            type_counts[key] = type_counts.get(key, 0) + 1

        series = item.issue.series
        s_entry = series_counts.setdefault(series.id, {"series": series, "count": 0})
        s_entry["count"] += 1

        publisher = series.publisher
        if publisher:
            p_entry = publisher_counts.setdefault(
                publisher.id, {"publisher": publisher, "count": 0}
            )
            p_entry["count"] += 1

    issue_type_breakdown = [
        {
            "key": k,
            "label": _ISSUE_TYPE_META[k][0],
            "color": _ISSUE_TYPE_META[k][1],
            "count": type_counts[k],
        }
        for k in ("CORE", "TIE_IN", "PROLOGUE", "EPILOGUE")
        if type_counts.get(k)
    ]

    series_breakdown = sorted(
        series_counts.values(),
        key=lambda e: (-e["count"], e["series"].name),
    )
    publisher_breakdown = sorted(
        publisher_counts.values(),
        key=lambda e: (-e["count"], e["publisher"].name),
    )

    issue_ids = [item.issue_id for item in reading_list_items]
    top6 = list(
        Creator.objects.filter(
            credits__issue_id__in=issue_ids,
            credits__role__name__in=_CREDIT_ROLE_NAMES,
        )
        .annotate(issue_count=Count("credits__issue", distinct=True))
        .order_by("-issue_count", "name")[:6]
    )
    creator_ids = [c.id for c in top6]
    role_map: dict[int, set[str]] = {}
    for credit in Credits.objects.filter(
        issue_id__in=issue_ids,
        creator_id__in=creator_ids,
        role__name__in=_CREDIT_ROLE_NAMES,
    ).prefetch_related(Prefetch("role", queryset=Role.objects.filter(name__in=_CREDIT_ROLE_NAMES))):
        for role in credit.role.all():
            role_map.setdefault(credit.creator_id, set()).add(role.name)

    featured_creators = [
        {
            "creator": c,
            "roles": ", ".join(
                sorted({str(_CREDIT_ROLE_DISPLAY.get(r, r)) for r in role_map.get(c.id, [])})
            ),
        }
        for c in top6
    ]

    top_characters = (
        Character.objects.filter(issues__in=issue_ids)
        .annotate(appearance_count=Count("issues", distinct=True))
        .order_by("-appearance_count", "name")[:12]
    )

    return {
        "issue_type_breakdown": issue_type_breakdown,
        "series_breakdown": series_breakdown,
        "publisher_breakdown": publisher_breakdown,
        "featured_creators": featured_creators,
        "top_characters": top_characters,
    }
