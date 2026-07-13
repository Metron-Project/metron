from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from comicsdb.models.issue import Issue
from issue_ratings.models import IssueRating

MIN_RATING = 1
MAX_RATING = 5


@login_required
@require_POST
def update_issue_rating(request, pk):
    """HTMX view to update the rating of an issue."""
    issue = get_object_or_404(Issue, pk=pk)

    rating_value = request.POST.get("rating")
    if rating_value:
        try:
            rating = int(rating_value)
            if MIN_RATING <= rating <= MAX_RATING:
                # Update or create rating
                IssueRating.objects.update_or_create(
                    issue=issue,
                    user=request.user,
                    defaults={"rating": rating},
                )
            elif rating == 0:  # Allow clearing the rating
                IssueRating.objects.filter(
                    issue=issue,
                    user=request.user,
                ).delete()
        except ValueError:
            pass

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

    # Return the updated rating partial
    return render(
        request,
        "issue_ratings/partials/issue_rating.html",
        {
            "issue": issue,
            "user_rating": user_rating,
            "average_rating": avg_data["avg"],
            "rating_count": avg_data["count"],
        },
    )
