"""
Shared helpers for HTMX star-rating update views.
"""

from comicsdb.models.common import MAX_RATING, MIN_RATING


def parse_rating_action(raw_value):
    """
    Parse a raw HTMX POST 'rating' value into an action.

    Returns ("set", rating) for a value in [MIN_RATING, MAX_RATING],
    ("clear", None) for the 0 sentinel, or None if the input is missing,
    non-numeric, or otherwise out of range (caller should no-op).
    """
    if not raw_value:
        return None
    try:
        rating = int(raw_value)
    except ValueError:
        return None
    if MIN_RATING <= rating <= MAX_RATING:
        return ("set", rating)
    if rating == 0:
        return ("clear", None)
    return None


def apply_rating_update(model, lookup, raw_value):
    """Set/update or clear a `model` row identified by `lookup` from a raw POST value."""
    action = parse_rating_action(raw_value)
    if action is None:
        return
    kind, rating = action
    if kind == "set":
        model.objects.update_or_create(**lookup, defaults={"rating": rating})
    else:
        model.objects.filter(**lookup).delete()
