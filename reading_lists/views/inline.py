"""HTMX endpoints for in-place rating and issue-type edits."""

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from comicsdb.views.ratings import apply_rating_update
from reading_lists.models import ReadingList, ReadingListItem, ReadingListRating
from reading_lists.services import can_manage_reading_list


@login_required
@require_POST
def update_reading_list_rating(request, slug):
    """HTMX view to update the rating of a reading list."""
    reading_list = get_object_or_404(ReadingList, slug=slug)

    # Only allow rating public lists
    if reading_list.is_private:
        return HttpResponseForbidden("Cannot rate private reading lists")

    # Prevent users from rating their own reading lists
    if reading_list.user == request.user:
        return HttpResponseForbidden("Cannot rate your own reading list")

    apply_rating_update(
        ReadingListRating,
        {"reading_list": reading_list, "user": request.user},
        request.POST.get("rating"),
    )

    # Get user's current rating and average
    user_rating = ReadingListRating.objects.filter(
        reading_list=reading_list,
        user=request.user,
    ).first()

    # Calculate average rating
    avg_data = reading_list.ratings.aggregate(
        avg=Avg("rating"),
        count=Count("id"),
    )

    # Return the updated rating partial
    return render(
        request,
        "partials/rating_widget.html",
        {
            "rated_object": reading_list,
            "rate_url_name": "reading-list:rate",
            "rate_url_arg": reading_list.slug,
            "user_rating": user_rating,
            "average_rating": avg_data["avg"],
            "rating_count": avg_data["count"],
            "show_ratings": True,
            "can_rate": True,
        },
    )


@login_required
def edit_issue_type(request, slug, item_pk):
    """HTMX view to show the edit form for issue type."""
    reading_list = get_object_or_404(ReadingList, slug=slug)

    # Check if user can manage this reading list
    if not can_manage_reading_list(request.user, reading_list):
        return HttpResponseForbidden("You do not have permission to edit this reading list")

    # Get the reading list item
    item = get_object_or_404(
        ReadingListItem,
        reading_list=reading_list,
        pk=item_pk,
    )

    # Return the edit form
    return render(
        request,
        "reading_lists/partials/readinglist_item_edit.html",
        {
            "item": item,
            "reading_list_slug": slug,
        },
    )


@login_required
@require_POST
def update_issue_type(request, slug, item_pk):
    """HTMX view to update the issue type of a reading list item."""
    reading_list = get_object_or_404(ReadingList, slug=slug)

    # Check if user can manage this reading list
    if not can_manage_reading_list(request.user, reading_list):
        return HttpResponseForbidden("You do not have permission to edit this reading list")

    # Get the reading list item
    item = get_object_or_404(
        ReadingListItem,
        reading_list=reading_list,
        pk=item_pk,
    )

    # Update the issue type
    issue_type = request.POST.get("issue_type", "")
    if issue_type in dict(ReadingListItem.IssueType.choices) or issue_type == "":
        item.issue_type = issue_type
        item.save()

    # Return the updated item display
    return render(
        request,
        "reading_lists/partials/readinglist_item.html",
        {
            "item": item,
            "reading_list_slug": slug,
            "is_owner": True,
        },
    )


@login_required
def cancel_edit_issue_type(request, slug, item_pk):
    """HTMX view to cancel editing and return to display mode."""
    reading_list = get_object_or_404(ReadingList, slug=slug)

    # Check if user can manage this reading list
    if not can_manage_reading_list(request.user, reading_list):
        return HttpResponseForbidden("You do not have permission to edit this reading list")

    # Get the reading list item
    item = get_object_or_404(
        ReadingListItem,
        reading_list=reading_list,
        pk=item_pk,
    )

    # Return the display view
    return render(
        request,
        "reading_lists/partials/readinglist_item.html",
        {
            "item": item,
            "reading_list_slug": slug,
            "is_owner": True,
        },
    )
