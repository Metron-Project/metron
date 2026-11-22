"""Collection operations shared by views (bulk adding issues)."""

from user_collection.models import CollectionItem


def add_issues_to_collection(user, issues, *, book_format, mark_as_read=False):
    """Add each of ``issues`` not already in ``user``'s collection.

    New items get quantity 1, ``book_format`` and, if ``mark_as_read``, are
    marked read. Only the given issues are checked for existing items, so this
    stays cheap however large the collection is.

    Returns:
        ``(added_count, skipped_count)``; skipped issues were already collected.
    """
    issues = list(issues)
    existing_ids = set(
        CollectionItem.objects.filter(
            user=user, issue_id__in=[issue.id for issue in issues]
        ).values_list("issue_id", flat=True)
    )
    new_items = [
        CollectionItem(
            user=user,
            issue=issue,
            quantity=1,
            book_format=book_format,
            is_read=mark_as_read,
        )
        for issue in issues
        if issue.id not in existing_ids
    ]
    CollectionItem.objects.bulk_create(new_items)
    return len(new_items), len(issues) - len(new_items)
