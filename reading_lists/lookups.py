"""Izaya lookups for reading_lists app."""

from izaya import ModelLookup, register

from reading_lists.models import ReadingList


@register
class ReadingListLookup(ModelLookup):
    """Lookup for searching reading lists.

    Only used to pick a list's previous/next entries, so results are limited to
    lists the requesting user can manage (matching ReadingListForm's choices).
    """

    model = ReadingList
    search_fields = ["name__unaccent__icontains"]
    rank_fields = ["name__unaccent"]

    def get_base_queryset(self):
        return super().get_base_queryset().select_related("user")

    def get_queryset(self, request):
        return super().get_queryset(request).manageable_by(request.user)
