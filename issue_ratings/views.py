from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from comicsdb.models.issue import Issue
from comicsdb.views.ratings import apply_rating_update
from issue_ratings.models import IssueRating


@login_required
@require_POST
def update_issue_rating(request, pk):
    """HTMX view to update the rating of an issue."""
    issue = get_object_or_404(Issue, pk=pk)

    if issue.is_released:
        apply_rating_update(
            IssueRating,
            {"issue": issue, "user": request.user},
            request.POST.get("rating"),
        )

    # Get user's current rating and average
    user_rating = IssueRating.objects.filter(
        issue=issue,
        user=request.user,
    ).first()

    # Calculate average rating
    avg_data = issue.ratings.aggregate(
        avg=Avg("rating"),
        count=Count("id"),
    )

    # Return the updated rating widget, plus an out-of-band update for the
    # average-rating summary shown in the page header so the two stay in sync.
    widget_html = render_to_string(
        "partials/rating_widget.html",
        {
            "rated_object": issue,
            "rate_url_name": "issue-ratings:rate",
            "rate_url_arg": issue.pk,
            "user_rating": user_rating,
            "average_rating": avg_data["avg"],
            "rating_count": avg_data["count"],
            "show_ratings": True,
            "can_rate": issue.is_released,
        },
        request=request,
    )
    summary_html = render_to_string(
        "partials/rating_summary.html",
        {
            "rated_object": issue,
            "average_rating": avg_data["avg"],
            "rating_count": avg_data["count"],
            "oob": True,
        },
        request=request,
    )
    return HttpResponse(widget_html + summary_html)
