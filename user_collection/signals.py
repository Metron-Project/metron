def sync_issue_rating_from_collection_item(sender, instance, **kwargs):
    """Keep the community IssueRating in sync with a user's personal collection rating.

    Deliberately does not bump the Issue's `modified`/cache -- see the
    comment on IssueViewSet.get_queryset()'s average_rating/rating_count
    annotation in api/views.py. Ratings change far more often than any
    other Issue field, so invalidating the API cache here would defeat
    detail caching for exactly the issues most worth caching.
    """
    from issue_ratings.models import IssueRating  # noqa: PLC0415

    if instance.rating is not None:
        IssueRating.objects.update_or_create(
            issue_id=instance.issue_id,
            user_id=instance.user_id,
            defaults={"rating": instance.rating},
        )
    else:
        IssueRating.objects.filter(
            issue_id=instance.issue_id,
            user_id=instance.user_id,
        ).delete()
