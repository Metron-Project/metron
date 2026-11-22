"""Reading list detail view and its lazy-loaded items."""

from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import DetailView

from comicsdb.views.mixins import LazyLoadMixin
from reading_lists.models import ReadingList, ReadingListItem, ReadingListRating
from reading_lists.services import (
    build_reading_list_breakdown_context,
    can_assign_reading_list_to_metron,
    can_manage_reading_list,
)

# Pagination constant for reading list detail view
READING_LIST_DETAIL_PAGINATE_BY = 50


class ReadingListDetailView(DetailView):
    """Display a single reading list with its issues."""

    model = ReadingList
    template_name = "reading_lists/readinglist_detail.html"
    context_object_name = "reading_list"

    def get_queryset(self):
        # Build the base queryset with all necessary prefetches and annotations
        queryset = (
            ReadingList.objects.select_related("user", "previous", "next")
            .prefetch_related(
                Prefetch(
                    "reading_list_items",
                    queryset=ReadingListItem.objects.select_related(
                        "issue__series__series_type",
                        "issue__series__publisher",
                    ).order_by("order"),
                ),
                Prefetch(
                    "ratings",
                    queryset=ReadingListRating.objects.select_related("user"),
                ),
            )
            .with_list_stats()
        )

        # If authenticated, prefetch user groups to avoid repeated queries
        if self.request.user.is_authenticated:
            queryset = queryset.prefetch_related(
                Prefetch(
                    "ratings",
                    queryset=ReadingListRating.objects.filter(user=self.request.user),
                    to_attr="user_rating_list",
                )
            )

        return queryset.visible_to(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reading_list = context["reading_list"]

        # Use prefetched reading_list_items (already ordered in get_queryset)
        reading_list_items = reading_list.reading_list_items.all()
        reading_list_items_count = len(reading_list_items)  # Use len() to avoid extra query

        context["reading_list_items_count"] = reading_list_items_count

        if reading_list_items_count > 0:
            context["reading_list_items"] = reading_list_items[:READING_LIST_DETAIL_PAGINATE_BY]

        # Check if user can manage this reading list
        if self.request.user.is_authenticated:
            context["is_owner"] = can_manage_reading_list(self.request.user, reading_list)
            context["can_assign_to_metron"] = reading_list.user.username != "Metron" and (
                can_assign_reading_list_to_metron(self.request.user)
            )
        else:
            context["is_owner"] = False
            context["can_assign_to_metron"] = False

        # Get user's rating from prefetched data
        user_rating = None
        if self.request.user.is_authenticated:
            user_rating_list = getattr(reading_list, "user_rating_list", [])
            user_rating = user_rating_list[0] if user_rating_list else None

        # Use annotated average rating (already calculated in get_queryset)
        context["user_rating"] = user_rating
        context["average_rating"] = reading_list.average_rating
        context["rating_count"] = reading_list.rating_count
        context["show_ratings"] = not reading_list.is_private
        context["can_rate"] = (
            self.request.user.is_authenticated and reading_list.user != self.request.user
        )

        # Hide previous/next links to lists this viewer can't see (e.g. private ones)
        context["previous_list"], context["next_list"] = reading_list.get_visible_nav(
            self.request.user
        )

        # Add annotated year data to context
        context["start_year"] = reading_list.start_year_annotated
        context["end_year"] = reading_list.end_year_annotated

        # Add issue-type/series/publisher breakdowns and featured creators/characters
        if reading_list_items_count > 0:
            context.update(build_reading_list_breakdown_context(reading_list_items))

        return context


class ReadingListItemsLoadMore(LazyLoadMixin, View):
    """HTMX endpoint for lazy loading more reading list items."""

    model = ReadingList
    relation_name = "reading_list_items"
    template_name = "reading_lists/partials/readinglist_item_list.html"
    context_object_name = "reading_list_items"
    slug_context_name = "reading_list_slug"

    def get(self, request, slug):
        """Handle GET request with privacy filtering."""
        # Apply same privacy filtering as ReadingListDetailView
        queryset = ReadingList.objects.visible_to(request.user)

        # Get the reading list with privacy filter applied
        parent_object = get_object_or_404(queryset, slug=slug)

        # Call the parent get method logic
        offset = int(request.GET.get("offset", 0))
        limit = self.get_limit()

        items = self.get_queryset(parent_object, offset, limit)
        total_count = self.get_total_count(parent_object)
        has_more = total_count > offset + limit

        context = self.get_context_data(parent_object, items, has_more, offset + limit, slug)
        return render(request, self.template_name, context)

    def get_queryset(self, parent_object, offset, limit):
        """Get paginated reading list items with related data."""
        items_qs = parent_object.reading_list_items.select_related(
            "issue__series__series_type"
        ).order_by("order")
        return items_qs[offset : offset + limit]

    def get_context_data(self, parent_object, items, has_more, next_offset, slug):
        """Add is_owner context for the remove button visibility."""
        context = super().get_context_data(parent_object, items, has_more, next_offset, slug)

        # Check if user can manage this reading list
        if self.request.user.is_authenticated:
            context["is_owner"] = can_manage_reading_list(self.request.user, parent_object)
        else:
            context["is_owner"] = False

        return context
