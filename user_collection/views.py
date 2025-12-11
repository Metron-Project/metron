from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Sum
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from comicsdb.models.issue import Issue
from user_collection.forms import AddIssuesFromSeriesForm, CollectionItemForm
from user_collection.models import CollectionItem


class CollectionListView(LoginRequiredMixin, ListView):
    """Display the current user's collection items."""

    model = CollectionItem
    template_name = "user_collection/collection_list.html"
    context_object_name = "collection_items"
    paginate_by = 50

    def get_queryset(self):
        return (
            CollectionItem.objects.filter(user=self.request.user)
            .select_related("issue__series__series_type", "issue__series__publisher")
            .order_by("issue__series__sort_name", "issue__cover_date")
        )


class CollectionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Display details of a single collection item."""

    model = CollectionItem
    template_name = "user_collection/collection_detail.html"
    context_object_name = "item"

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
        messages.success(self.request, "Item added to your collection!")
        return super().form_valid(form)

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
        messages.success(self.request, "Collection item updated!")
        return super().form_valid(form)

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

        context.update(
            {
                "total_items": total_items,
                "total_quantity": total_quantity,
                "total_value": total_value or 0,
                "read_count": read_count,
                "unread_count": unread_count,
                "format_counts": format_counts,
                "top_series": top_series,
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
                        book_format=CollectionItem.BookFormat.PRINT,
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
