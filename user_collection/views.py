from datetime import datetime

from chartkick.django import PieChart
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Count, F, Sum
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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
from user_collection.forms import AddIssuesFromSeriesForm, CollectionItemForm
from user_collection.models import GRADE_CHOICES, CollectionItem, ReadDate

# Rating constants
MIN_RATING = 1
MAX_RATING = 5


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

        messages.success(self.request, "Item added to your collection!")
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

        messages.success(self.request, "Collection item updated!")
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
        messages.success(self.request, "Item removed from your collection.")
        return super().form_valid(form)


class CollectionStatsView(LoginRequiredMixin, TemplateView):
    """Display statistics about the user's collection."""

    template_name = "user_collection/collection_stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = CollectionItem.objects.filter(user=self.request.user)

        # Calculate statistics
        total_items = queryset.count()
        total_quantity = queryset.aggregate(Sum("quantity"))["quantity__sum"] or 0

        # Calculate total value
        total_value_result = queryset.aggregate(Sum("purchase_price"))
        total_value = total_value_result["purchase_price__sum"]

        # Reading statistics
        read_count = queryset.filter(is_read=True).count()
        unread_count = queryset.filter(is_read=False).count()

        # Format breakdown
        format_counts = queryset.values("book_format").annotate(count=Count("id"))

        # Get top series
        top_series = (
            queryset.values("issue__series__name", "issue__series__id")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # Create chart data
        # Publisher distribution
        publisher_data = (
            queryset.values("issue__series__publisher__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        publisher_dict = {
            item["issue__series__publisher__name"] or "Unknown": item["count"]
            for item in publisher_data
        }
        publisher_chart = PieChart(
            publisher_dict,
            title="Issues by Publisher",
            thousands=",",
            legend="bottom",
        )

        # Series type distribution
        series_type_data = (
            queryset.values("issue__series__series_type__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        series_type_dict = {
            item["issue__series__series_type__name"] or "Unknown": item["count"]
            for item in series_type_data
        }
        series_type_chart = PieChart(
            series_type_dict,
            title="Issues by Series Type",
            thousands=",",
            legend="bottom",
        )

        # Format distribution
        format_dict = {}
        for item in format_counts:
            format_name = dict(CollectionItem.BookFormat.choices).get(
                item["book_format"], "Unknown"
            )
            format_dict[format_name] = item["count"]
        format_chart = PieChart(
            format_dict,
            title="Issues by Format",
            thousands=",",
            legend="bottom",
        )

        context.update(
            {
                "total_items": total_items,
                "total_quantity": total_quantity,
                "total_value": total_value or 0,
                "read_count": read_count,
                "unread_count": unread_count,
                "format_counts": format_counts,
                "top_series": top_series,
                "publisher_chart": publisher_chart,
                "series_type_chart": series_type_chart,
                "format_chart": format_chart,
            }
        )

        return context


class AddIssuesFromSeriesView(LoginRequiredMixin, FormView):
    """Add multiple issues from a series to the collection."""

    form_class = AddIssuesFromSeriesForm
    template_name = "user_collection/add_issues_from_series.html"
    success_url = reverse_lazy("user_collection:list")

    def form_valid(self, form):  # noqa: PLR0912, PLR0915
        series = form.cleaned_data["series"]
        range_type = form.cleaned_data["range_type"]
        start_number = form.cleaned_data.get("start_number")
        end_number = form.cleaned_data.get("end_number")
        default_format = form.cleaned_data.get("default_format") or CollectionItem.BookFormat.PRINT
        mark_as_read = form.cleaned_data.get("mark_as_read", False)

        # Get all issues from the series, ordered by cover date
        issues_queryset = Issue.objects.filter(series=series).order_by("cover_date", "number")

        # Apply range filtering if specified
        if range_type == "range":
            # Build filter conditions based on provided numbers
            if start_number and end_number:
                # Filter issues between start and end numbers
                all_issues = list(issues_queryset)
                filtered_issues = []
                in_range = False

                for issue in all_issues:
                    # Check if this is the start issue
                    if issue.number == start_number:
                        in_range = True

                    # If we're in range, add the issue
                    if in_range:
                        filtered_issues.append(issue)

                    # Check if this is the end issue
                    if issue.number == end_number:
                        break

                issues_to_add = filtered_issues
            elif start_number:
                # Start from a specific issue to the end
                all_issues = list(issues_queryset)
                filtered_issues = []
                found_start = False

                for issue in all_issues:
                    if issue.number == start_number:
                        found_start = True
                    if found_start:
                        filtered_issues.append(issue)

                issues_to_add = filtered_issues
            elif end_number:
                # From beginning to a specific issue
                all_issues = list(issues_queryset)
                filtered_issues = []

                for issue in all_issues:
                    filtered_issues.append(issue)
                    if issue.number == end_number:
                        break

                issues_to_add = filtered_issues
            else:
                issues_to_add = list(issues_queryset)
        else:
            # Add all issues
            issues_to_add = list(issues_queryset)

        # Get existing issue IDs to avoid duplicates
        existing_issue_ids = set(
            CollectionItem.objects.filter(user=self.request.user).values_list("issue_id", flat=True)
        )

        # Create collection items for new issues
        new_items = []
        skipped_count = 0

        for issue in issues_to_add:
            if issue.id not in existing_issue_ids:
                new_items.append(
                    CollectionItem(
                        user=self.request.user,
                        issue=issue,
                        quantity=1,
                        book_format=default_format,
                        is_read=mark_as_read,
                    )
                )
            else:
                skipped_count += 1

        # Bulk create all new items
        if new_items:
            CollectionItem.objects.bulk_create(new_items)
            added_count = len(new_items)
            read_status_msg = " (marked as read)" if mark_as_read else ""

            if skipped_count > 0:
                issue_word = "issue" if added_count == 1 else "issues"
                skipped_word = "issue" if skipped_count == 1 else "issues"
                messages.success(
                    self.request,
                    f"Added {added_count} {issue_word} to your collection{read_status_msg}. "
                    f"Skipped {skipped_count} {skipped_word} already in your collection.",
                )
            else:
                messages.success(
                    self.request,
                    f"Added {added_count} issue{'s' if added_count != 1 else ''} "
                    f"to your collection{read_status_msg}!",
                )
        else:
            messages.info(
                self.request, "All issues from this series are already in your collection."
            )

        return super().form_valid(form)


@login_required
@require_POST
def update_rating(request, pk):
    """HTMX view to update the rating of a collection item."""
    item = get_object_or_404(CollectionItem, pk=pk, user=request.user)

    rating_value = request.POST.get("rating")
    if rating_value:
        try:
            rating = int(rating_value)
            # Allow ratings from MIN_RATING to MAX_RATING
            if MIN_RATING <= rating <= MAX_RATING:
                item.rating = rating
            elif rating == 0:  # Allow clearing the rating
                item.rating = None
            item.save(update_fields=["rating"])
        except ValueError:
            pass

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
            except (ValueError, TypeError):
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
        item.date_read = latest
        item.save(update_fields=["date_read"])
    else:
        item.is_read = False
        item.date_read = None
        item.save(update_fields=["is_read", "date_read"])

    return render(request, "user_collection/partials/read_dates_list.html", {"item": item})
