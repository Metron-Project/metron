from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Count, F
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext as _, ngettext
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from comicsdb.filters.collection import CollectionViewFilter
from comicsdb.models.issue import Issue
from comicsdb.models.publisher import Publisher
from comicsdb.models.series import Series, SeriesType
from comicsdb.views.issue_list_helpers import filter_issues_by_number_range
from comicsdb.views.ratings import parse_rating_action
from user_collection.forms import AddIssuesFromSeriesForm, CollectionItemForm
from user_collection.models import GRADE_CHOICES, CollectionItem, ReadDate
from user_collection.services import add_issues_to_collection
from user_collection.stats import collection_charts, collection_summary, top_series


class CollectionListView(LoginRequiredMixin, ListView):
    """Display the current user's collection items."""

    model = CollectionItem
    template_name = "user_collection/collection_list.html"
    context_object_name = "collection_items"
    paginate_by = 50

    def get_queryset(self):
        queryset = (
            CollectionItem.objects.filter(user=self.request.user)
            .select_related(
                "issue__series__series_type",
                "issue__series__publisher",
                "issue__series__imprint",
            )
            .order_by("issue__series__sort_name", "issue__cover_date")
        )
        # Apply filters
        filtered = CollectionViewFilter(self.request.GET, queryset=queryset)
        return filtered.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter options for the template
        context["series_type"] = SeriesType.objects.values("id", "name").order_by("name")
        context["publishers"] = Publisher.objects.values("id", "name").order_by("name")
        context["book_formats"] = CollectionItem.BookFormat.choices
        context["grade_choices"] = GRADE_CHOICES
        context["grading_companies"] = CollectionItem.GradingCompany.choices
        context["rating_choices"] = [(i, i) for i in range(1, 6)]
        # Check if any filters are active (excluding page parameter)
        context["has_active_filters"] = any(key != "page" for key in self.request.GET)
        return context


class CollectionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Display details of a single collection item."""

    model = CollectionItem
    template_name = "user_collection/collection_detail.html"
    context_object_name = "item"

    def get_queryset(self):
        """Optimize query to include issue details."""
        return CollectionItem.objects.select_related(
            "issue",
            "issue__series",
            "issue__series__publisher",
        )

    def test_func(self):
        """Only allow the owner to view their collection item."""
        item = self.get_object()
        return item.user == self.request.user


class CollectionCreateView(LoginRequiredMixin, CreateView):
    """Create a new collection item."""

    model = CollectionItem
    form_class = CollectionItemForm
    template_name = "user_collection/collection_form.html"

    def get_form_kwargs(self):
        """Pass the current user to the form for validation."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """Set the user to the current user before saving."""
        form.instance.user = self.request.user
        response = super().form_valid(form)

        # If is_read is checked and there are no read dates, add one
        if form.instance.is_read and not form.instance.read_dates.exists():
            form.instance.add_read_date()

        messages.success(self.request, _("Item added to your collection!"))
        return response

    def get_success_url(self):
        return reverse("user_collection:list")


class CollectionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update an existing collection item."""

    model = CollectionItem
    form_class = CollectionItemForm
    template_name = "user_collection/collection_form.html"

    def test_func(self):
        """Only allow the owner to edit their collection item."""
        item = self.get_object()
        return item.user == self.request.user

    def get_form_kwargs(self):
        """Pass the current user to the form for validation."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)

        # If is_read is checked and there are no read dates, add one
        if form.instance.is_read and not form.instance.read_dates.exists():
            form.instance.add_read_date()

        messages.success(self.request, _("Collection item updated!"))
        return response

    def get_success_url(self):
        return reverse("user_collection:detail", kwargs={"pk": self.object.pk})


class CollectionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a collection item."""

    model = CollectionItem
    template_name = "user_collection/collection_confirm_delete.html"
    context_object_name = "item"
    success_url = reverse_lazy("user_collection:list")

    def test_func(self):
        """Only allow the owner to delete their collection item."""
        item = self.get_object()
        return item.user == self.request.user

    def form_valid(self, form):
        messages.success(self.request, _("Item removed from your collection."))
        return super().form_valid(form)


class CollectionStatsView(LoginRequiredMixin, TemplateView):
    """Display statistics about the user's collection."""

    template_name = "user_collection/collection_stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        summary = collection_summary(user)
        context.update(summary)
        context["total_value"] = summary["total_value"] or 0
        context["top_series"] = top_series(user)
        context.update(collection_charts(user, summary["format_counts"]))
        return context


def _bulk_add_message(added_count, skipped_count, mark_as_read):
    """Return ``(message_level, message)`` summarizing a bulk add to the collection."""
    if not added_count:
        return messages.INFO, _("All issues from this series are already in your collection.")

    added_phrase = ngettext(
        "Added %(count)d issue to your collection",
        "Added %(count)d issues to your collection",
        added_count,
    ) % {"count": added_count}
    if mark_as_read:
        added_phrase = _("%(phrase)s (marked as read)") % {"phrase": added_phrase}

    if not skipped_count:
        return messages.SUCCESS, _("%(added)s!") % {"added": added_phrase}
    skipped_phrase = ngettext(
        "Skipped %(count)d issue already in your collection.",
        "Skipped %(count)d issues already in your collection.",
        skipped_count,
    ) % {"count": skipped_count}
    return messages.SUCCESS, _("%(added)s. %(skipped)s") % {
        "added": added_phrase,
        "skipped": skipped_phrase,
    }


class AddIssuesFromSeriesView(LoginRequiredMixin, FormView):
    """Add multiple issues from a series to the collection."""

    form_class = AddIssuesFromSeriesForm
    template_name = "user_collection/add_issues_from_series.html"
    success_url = reverse_lazy("user_collection:list")

    def form_valid(self, form):
        series = form.cleaned_data["series"]
        range_type = form.cleaned_data["range_type"]
        start_number = form.cleaned_data.get("start_number")
        end_number = form.cleaned_data.get("end_number")
        default_format = form.cleaned_data.get("default_format") or CollectionItem.BookFormat.PRINT
        mark_as_read = form.cleaned_data.get("mark_as_read", False)

        # Get all issues from the series, ordered by cover date
        issues_queryset = Issue.objects.filter(series=series).order_by("cover_date", "number")

        if range_type == "range":
            issues_to_add = filter_issues_by_number_range(issues_queryset, start_number, end_number)
        else:
            issues_to_add = list(issues_queryset)

        added_count, skipped_count = add_issues_to_collection(
            self.request.user,
            issues_to_add,
            book_format=default_format,
            mark_as_read=mark_as_read,
        )
        level, message = _bulk_add_message(added_count, skipped_count, mark_as_read)
        messages.add_message(self.request, level, message)

        return super().form_valid(form)


@login_required
@require_POST
def update_rating(request, pk):
    """HTMX view to update the rating of a collection item."""
    item = get_object_or_404(CollectionItem, pk=pk, user=request.user)

    action = parse_rating_action(request.POST.get("rating"))
    if action is not None:
        kind, rating = action
        item.rating = rating if kind == "set" else None
        item.save(update_fields=["rating"])

    # Return the updated star rating partial
    return render(
        request,
        "user_collection/partials/star_rating.html",
        {"item": item},
    )


class MissingIssuesListView(LoginRequiredMixin, ListView):
    """Display series where the user is missing issues."""

    model = Series
    template_name = "user_collection/missing_issues_list.html"
    context_object_name = "series_list"
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user

        # Annotate all series with total and owned issue counts
        # Then filter to only show series with missing issues
        return (
            Series.objects.annotate(
                total_issues=Count("issues", distinct=True),
                owned_issues=Count(
                    "issues", filter=models.Q(issues__in_collections__user=user), distinct=True
                ),
            )
            .annotate(missing_count=F("total_issues") - F("owned_issues"))
            .filter(owned_issues__gt=0, missing_count__gt=0)
            .select_related("publisher", "series_type", "imprint")
            .order_by("-missing_count", "sort_name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add total count of series with missing issues
        context["series_with_missing_count"] = self.get_queryset().count()
        return context


class MissingIssuesDetailView(LoginRequiredMixin, ListView):
    """Display specific missing issues for a series."""

    model = Issue
    template_name = "user_collection/missing_issues_detail.html"
    context_object_name = "missing_issues"
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user
        series_id = self.kwargs["series_id"]

        # Get user's owned issue IDs for this series
        owned_issue_ids = CollectionItem.objects.filter(
            user=user, issue__series_id=series_id
        ).values_list("issue_id", flat=True)

        # Get all issues from series that user doesn't own
        return (
            Issue.objects.filter(series_id=series_id)
            .exclude(id__in=owned_issue_ids)
            .select_related("series", "series__publisher", "series__series_type")
            .order_by("cover_date", "number")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series_id = self.kwargs["series_id"]
        user = self.request.user

        # Get series object with related data
        series = get_object_or_404(
            Series.objects.select_related("publisher", "series_type", "imprint"),
            id=series_id,
        )

        # Calculate ownership stats
        total_issues = series.issues.count()
        owned_issues = CollectionItem.objects.filter(user=user, issue__series=series).count()
        missing_count = total_issues - owned_issues
        completion_pct = (owned_issues / total_issues * 100) if total_issues > 0 else 0

        context.update(
            {
                "series": series,
                "total_issues": total_issues,
                "owned_issues": owned_issues,
                "missing_count": missing_count,
                "completion_percentage": round(completion_pct, 1),
            }
        )

        return context


class ReadingHistoryListView(LoginRequiredMixin, ListView):
    """Display the user's reading history."""

    model = CollectionItem
    template_name = "user_collection/reading_history.html"
    context_object_name = "history_items"
    paginate_by = 50

    def get_queryset(self):
        return (
            CollectionItem.objects.filter(user=self.request.user, is_read=True)
            .select_related(
                "issue__series__series_type",
                "issue__series__publisher",
                "issue__series__imprint",
            )
            .annotate(
                read_count=Count(
                    "read_dates",
                    filter=models.Q(read_dates__read_date__date=TruncDate(F("date_read"))),
                )
            )
            .order_by("-date_read", "-modified")
        )


@login_required
@require_POST
def add_read_date(request, pk):
    """HTMX view to add a new read date to a collection item."""
    item = get_object_or_404(CollectionItem, pk=pk, user=request.user)

    read_date_str = request.POST.get("read_date", "").strip()
    if read_date_str:
        try:
            # Try parsing Bulma Calendar format (yyyy-MM-dd HH:mm)
            read_date = datetime.strptime(read_date_str, "%Y-%m-%d %H:%M")
            # Make it timezone-aware
            read_date = timezone.make_aware(read_date)
            item.add_read_date(read_date)
        except ValueError:
            # Fall back to Django's parse_datetime for other formats
            try:
                read_date = parse_datetime(read_date_str)
                if read_date:
                    item.add_read_date(read_date)
                else:
                    item.add_read_date()  # Invalid format, use current time
            except ValueError, TypeError:
                item.add_read_date()  # Use current time on error
    else:
        item.add_read_date()  # Use current time if empty

    return render(request, "user_collection/partials/read_dates_list.html", {"item": item})


@login_required
@require_POST
def delete_read_date(request, pk, read_date_pk):
    """HTMX view to delete a specific read date."""
    item = get_object_or_404(CollectionItem, pk=pk, user=request.user)
    read_date = get_object_or_404(ReadDate, pk=read_date_pk, collection_item=item)

    read_date.delete()

    # Update backward compatibility fields
    latest = item.get_latest_read_date()
    if latest:
        item.is_read = True
        item.date_read = latest
        item.save(update_fields=["is_read", "date_read"])
    else:
        item.is_read = False
        item.date_read = None
        item.save(update_fields=["is_read", "date_read"])

    return render(request, "user_collection/partials/read_dates_list.html", {"item": item})
