from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Avg, Count, Max, Min, Prefetch, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from comicsdb.filters.reading_list import ReadingListViewFilter
from comicsdb.models.issue import Issue
from comicsdb.views.mixins import LazyLoadMixin, SearchMixin
from reading_lists.forms import (
    AddIssuesFromArcForm,
    AddIssuesFromSeriesForm,
    AddIssueWithSearchForm,
    ReadingListForm,
)
from reading_lists.models import ReadingList, ReadingListItem, ReadingListRating
from users.models import CustomUser

# Pagination constant for reading list detail view
READING_LIST_DETAIL_PAGINATE_BY = 50

# Rating constants
MIN_RATING = 1
MAX_RATING = 5


def can_manage_reading_list(user, reading_list):
    """Check if a user can manage (edit/delete) a reading list.

    Users can manage a list if they are:
    - The owner of the list
    - Staff editing a Metron list
    - Member of 'reading list editor' group editing a Metron list
    """
    is_owner = reading_list.user == user

    if reading_list.user.username == "Metron":
        is_staff = user.is_staff
        is_editor_group = user.groups.filter(name="reading list editor").exists()
        return is_owner or is_staff or is_editor_group

    return is_owner


class ReadingListListView(ListView):
    """Display all public reading lists, plus user's own lists if authenticated."""

    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        queryset = ReadingList.objects.select_related("user").annotate(
            issue_count=Count("issues"),
            average_rating=Avg("ratings__rating"),
            rating_count=Count("ratings", distinct=True),
        )

        if self.request.user.is_authenticated:
            # If admin or reading list editor, show public lists + user's own lists + Metron's lists
            is_editor = self.request.user.groups.filter(name="reading list editor").exists()
            if self.request.user.is_staff or is_editor:
                try:
                    metron_user = CustomUser.objects.get(username="Metron")
                    queryset = queryset.filter(
                        Q(is_private=False) | Q(user=self.request.user) | Q(user=metron_user)
                    ).distinct()
                except CustomUser.DoesNotExist:
                    queryset = queryset.filter(
                        Q(is_private=False) | Q(user=self.request.user)
                    ).distinct()
            else:
                # Show public lists + user's own lists (including private)
                queryset = queryset.filter(
                    Q(is_private=False) | Q(user=self.request.user)
                ).distinct()
        else:
            # Show only public lists
            queryset = queryset.filter(is_private=False)

        # Apply filters
        filtered = ReadingListViewFilter(self.request.GET, queryset=queryset)
        return filtered.qs.order_by("name", "attribution_source", "user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter options for the template
        context["attribution_sources"] = ReadingList.AttributionSource.choices
        # Check if any filters are active (excluding page parameter)
        context["has_active_filters"] = any(key != "page" for key in self.request.GET)
        return context


class SearchReadingListListView(SearchMixin, ReadingListListView):
    """Search reading lists by name, user, or attribution source."""

    def get_search_fields(self):
        """Search across name, username, and attribution source display text."""
        return ["name__icontains", "user__username__icontains", "attribution_source__icontains"]

    def get_queryset(self):
        """Get queryset without applying the filter (SearchMixin handles search)."""
        queryset = ReadingList.objects.select_related("user").annotate(
            issue_count=Count("issues"),
            average_rating=Avg("ratings__rating"),
            rating_count=Count("ratings", distinct=True),
        )

        if self.request.user.is_authenticated:
            # If admin or reading list editor, show public lists + user's own lists + Metron's lists
            is_editor = self.request.user.groups.filter(name="reading list editor").exists()
            if self.request.user.is_staff or is_editor:
                try:
                    metron_user = CustomUser.objects.get(username="Metron")
                    queryset = queryset.filter(
                        Q(is_private=False) | Q(user=self.request.user) | Q(user=metron_user)
                    ).distinct()
                except CustomUser.DoesNotExist:
                    queryset = queryset.filter(
                        Q(is_private=False) | Q(user=self.request.user)
                    ).distinct()
            else:
                # Show public lists + user's own lists (including private)
                queryset = queryset.filter(
                    Q(is_private=False) | Q(user=self.request.user)
                ).distinct()
        else:
            # Show only public lists
            queryset = queryset.filter(is_private=False)

        # Apply SearchMixin search logic (not the filter)
        if query := self.request.GET.get("q"):
            queryset = self.get_search_queryset(queryset, query)

        return queryset.order_by("name", "attribution_source", "user")


class UserReadingListListView(LoginRequiredMixin, ListView):
    """Display only the current user's reading lists."""

    model = ReadingList
    template_name = "reading_lists/user_readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        return (
            ReadingList.objects.filter(user=self.request.user)
            .annotate(
                issue_count=Count("issues"),
                average_rating=Avg("ratings__rating"),
                rating_count=Count("ratings", distinct=True),
            )
            .order_by("name", "attribution_source", "user")
        )


class ReadingListDetailView(DetailView):
    """Display a single reading list with its issues."""

    model = ReadingList
    template_name = "reading_lists/readinglist_detail.html"
    context_object_name = "reading_list"

    def get_queryset(self):
        # Build the base queryset with all necessary prefetches and annotations
        queryset = (
            ReadingList.objects.select_related("user")
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
            .annotate(
                start_year_annotated=Min("reading_list_items__issue__cover_date__year"),
                end_year_annotated=Max("reading_list_items__issue__cover_date__year"),
                average_rating_annotated=Avg("ratings__rating"),
                rating_count_annotated=Count("ratings", distinct=True),
            )
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

        # If not authenticated, only show public lists
        if not self.request.user.is_authenticated:
            return queryset.filter(is_private=False)

        # If admin or reading list editor, show public lists + user's own lists + Metron's lists
        is_editor = self.request.user.groups.filter(name="reading list editor").exists()
        if self.request.user.is_staff or is_editor:
            try:
                metron_user = CustomUser.objects.get(username="Metron")
                return queryset.filter(
                    Q(is_private=False) | Q(user=self.request.user) | Q(user=metron_user)
                )
            except CustomUser.DoesNotExist:
                pass

        # If authenticated, show public lists + user's own lists
        return queryset.filter(Q(is_private=False) | Q(user=self.request.user))

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
        else:
            context["is_owner"] = False

        # Get user's rating from prefetched data
        user_rating = None
        if self.request.user.is_authenticated:
            user_rating_list = getattr(reading_list, "user_rating_list", [])
            user_rating = user_rating_list[0] if user_rating_list else None

        # Use annotated average rating (already calculated in get_queryset)
        context["user_rating"] = user_rating
        context["average_rating"] = reading_list.average_rating_annotated
        context["rating_count"] = reading_list.rating_count_annotated

        # Add annotated year data to context
        context["start_year"] = reading_list.start_year_annotated
        context["end_year"] = reading_list.end_year_annotated

        # Prefetch publishers efficiently
        if reading_list_items_count > 0:
            # Get unique publishers from already-prefetched data
            publishers = {}
            for item in reading_list_items:
                publisher = item.issue.series.publisher
                if publisher and publisher.id not in publishers:
                    publishers[publisher.id] = publisher
            context["publishers"] = sorted(publishers.values(), key=lambda p: p.name)
        else:
            context["publishers"] = []

        return context


class ReadingListCreateView(LoginRequiredMixin, CreateView):
    """Create a new reading list."""

    model = ReadingList
    form_class = ReadingListForm
    template_name = "reading_lists/readinglist_form.html"

    def get_form(self, form_class=None):
        """Customize form to exclude attribution fields for non-admin users."""
        form = super().get_form(form_class)
        if not self.request.user.is_staff:
            # Remove attribution fields for non-admin users
            form.fields.pop("attribution_source", None)
            form.fields.pop("attribution_url", None)
        return form

    def form_valid(self, form):
        # Set the user to the current user
        form.instance.user = self.request.user
        messages.success(self.request, f"Reading list '{form.instance.name}' created!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create Reading List"
        context["button_text"] = "Create"
        return context


class ReadingListUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update an existing reading list."""

    model = ReadingList
    form_class = ReadingListForm
    template_name = "reading_lists/readinglist_form.html"

    def test_func(self):
        """Only allow authorized users to edit the list."""
        reading_list = self.get_object()
        return can_manage_reading_list(self.request.user, reading_list)

    def get_form(self, form_class=None):
        """Customize form to exclude attribution fields for non-admin users."""
        form = super().get_form(form_class)
        if not self.request.user.is_staff:
            # Remove attribution fields for non-admin users
            form.fields.pop("attribution_source", None)
            form.fields.pop("attribution_url", None)
        return form

    def form_valid(self, form):
        # Update the edited_by field (via the modified timestamp)
        messages.success(self.request, f"Reading list '{form.instance.name}' updated!")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit Reading List"
        context["button_text"] = "Update"
        return context


class ReadingListDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a reading list."""

    model = ReadingList
    template_name = "reading_lists/readinglist_confirm_delete.html"
    success_url = reverse_lazy("reading-list:my-lists")

    def test_func(self):
        """Only allow authorized users to delete the list."""
        reading_list = self.get_object()
        return can_manage_reading_list(self.request.user, reading_list)

    def form_valid(self, form):
        messages.success(self.request, f"Reading list '{self.object.name}' deleted!")
        return super().form_valid(form)


class RemoveIssueFromReadingListView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Remove an issue from a reading list."""

    model = ReadingListItem
    template_name = "reading_lists/remove_issue_confirm.html"

    def dispatch(self, request, *args, **kwargs):
        self.reading_list = get_object_or_404(ReadingList, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Only allow authorized users to remove issues."""
        return can_manage_reading_list(self.request.user, self.reading_list)

    def get_object(self):
        return get_object_or_404(
            ReadingListItem,
            reading_list=self.reading_list,
            pk=self.kwargs["item_pk"],
        )

    def get_success_url(self):
        messages.success(
            self.request,
            f"Removed {self.object.issue} from '{self.reading_list.name}'!",
        )
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})


class AddIssueWithAutocompleteView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Add an issue to a reading list using autocomplete search."""

    form_class = AddIssueWithSearchForm
    template_name = "reading_lists/add_issue_autocomplete.html"

    def dispatch(self, request, *args, **kwargs):
        self.reading_list = get_object_or_404(ReadingList, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Only allow authorized users to add issues."""
        return can_manage_reading_list(self.request.user, self.reading_list)

    def form_valid(self, form):  # noqa: PLR0912
        new_issues = form.cleaned_data["issues"]
        issue_order_str = form.cleaned_data.get("issue_order", "")

        # Parse the issue order (contains both existing and new issue IDs)
        if issue_order_str:
            issue_order = [int(pk) for pk in issue_order_str.split(",") if pk.strip()]
        else:
            # Default to existing issues + new issues
            existing_items = self.reading_list.reading_list_items.order_by("order")
            issue_order = [item.issue.pk for item in existing_items] + [
                issue.pk for issue in new_issues
            ]

        # Get existing issue IDs in the reading list
        existing_issue_ids = set(
            self.reading_list.reading_list_items.values_list("issue_id", flat=True)
        )
        new_issue_ids = {issue.pk for issue in new_issues}

        added_count = 0
        reordered_count = 0
        skipped_count = 0
        added_issues = []

        # Process all issues in the specified order
        for new_order, issue_pk in enumerate(issue_order, start=1):
            if issue_pk in existing_issue_ids:
                # Update the order of an existing issue
                item = ReadingListItem.objects.get(
                    reading_list=self.reading_list, issue_id=issue_pk
                )
                if item.order != new_order:
                    item.order = new_order
                    item.save()
                    reordered_count += 1
            elif issue_pk in new_issue_ids:
                # Check if this new issue is already in the list (shouldn't happen, but be safe)
                if ReadingListItem.objects.filter(
                    reading_list=self.reading_list, issue_id=issue_pk
                ).exists():
                    skipped_count += 1
                    continue

                # Create a new reading list item
                try:
                    issue = new_issues.get(pk=issue_pk)
                    ReadingListItem.objects.create(
                        reading_list=self.reading_list,
                        issue=issue,
                        order=new_order,
                    )
                    added_count += 1
                    added_issues.append(str(issue))
                except Issue.DoesNotExist:
                    continue

        # Provide feedback
        messages_to_show = []
        if added_count > 0:
            if added_count == 1:
                messages_to_show.append(f"Added {added_issues[0]}")
            else:
                messages_to_show.append(f"Added {added_count} issue(s)")

        if reordered_count > 0:
            messages_to_show.append(f"reordered {reordered_count} existing issue(s)")

        if messages_to_show:
            messages.success(
                self.request,
                f"{', '.join(messages_to_show)} in '{self.reading_list.name}'!",
            )

        if skipped_count > 0:
            messages.info(
                self.request,
                f"Skipped {skipped_count} duplicate issue(s).",
            )

        if added_count == 0 and reordered_count == 0 and skipped_count == 0:
            messages.info(self.request, "No changes were made.")

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reading_list"] = self.reading_list
        # Get existing issues in the reading list
        context["existing_items"] = self.reading_list.reading_list_items.select_related(
            "issue__series__series_type"
        ).order_by("order")
        return context


class AddIssuesFromSeriesView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Add multiple issues from a series to a reading list."""

    form_class = AddIssuesFromSeriesForm
    template_name = "reading_lists/add_issues_from_series.html"

    def dispatch(self, request, *args, **kwargs):
        self.reading_list = get_object_or_404(ReadingList, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Only allow authorized users to add issues."""
        return can_manage_reading_list(self.request.user, self.reading_list)

    def form_valid(self, form):  # noqa: PLR0912, PLR0915
        series = form.cleaned_data["series"]
        range_type = form.cleaned_data["range_type"]
        start_number = form.cleaned_data.get("start_number")
        end_number = form.cleaned_data.get("end_number")
        position = form.cleaned_data["position"]

        # Get all issues from the series, ordered by cover date
        issues_queryset = Issue.objects.filter(series=series).order_by("cover_date", "number")

        # Apply range filtering if specified
        if range_type == "range":
            # Build filter conditions based on provided numbers
            if start_number and end_number:
                # Filter issues between start and end numbers
                # Since number is a CharField, we need to handle this carefully
                # We'll get all issues and filter in Python for flexibility
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
            self.reading_list.reading_list_items.values_list("issue_id", flat=True)
        )

        # Filter out issues already in the reading list
        new_issues = [issue for issue in issues_to_add if issue.pk not in existing_issue_ids]

        if not new_issues:
            messages.info(
                self.request,
                f"No new issues to add. All issues from {series} are already in the list.",
            )
            return redirect(self.get_success_url())

        # Determine starting order based on position
        if position == "beginning":
            # Insert at the beginning - need to reorder existing items
            start_order = 1
            # Shift existing items down
            existing_items = self.reading_list.reading_list_items.order_by("order")
            for idx, item in enumerate(existing_items, start=len(new_issues) + 1):
                if item.order != idx:
                    item.order = idx
                    item.save()
        else:
            # Add at the end
            max_order = (
                self.reading_list.reading_list_items.aggregate(models.Max("order"))["order__max"]
                or 0
            )
            start_order = max_order + 1

        # Create reading list items for new issues
        items_to_create = [
            ReadingListItem(
                reading_list=self.reading_list,
                issue=issue,
                order=start_order + idx,
            )
            for idx, issue in enumerate(new_issues)
        ]

        ReadingListItem.objects.bulk_create(items_to_create)

        # Provide feedback
        position_text = "at the beginning" if position == "beginning" else "at the end"
        messages.success(
            self.request,
            f"Added {len(new_issues)} issue(s) from {series} {position_text} "
            f"of '{self.reading_list.name}'!",
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reading_list"] = self.reading_list
        return context


class AddIssuesFromArcView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Add all issues from a story arc to a reading list."""

    form_class = AddIssuesFromArcForm
    template_name = "reading_lists/add_issues_from_arc.html"

    def dispatch(self, request, *args, **kwargs):
        self.reading_list = get_object_or_404(ReadingList, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Only allow authorized users to add issues."""
        return can_manage_reading_list(self.request.user, self.reading_list)

    def form_valid(self, form):
        arc = form.cleaned_data["arc"]
        position = form.cleaned_data["position"]

        # Get all issues from the arc, ordered by cover date
        issues_queryset = arc.issues.order_by("cover_date", "number")
        issues_to_add = list(issues_queryset)

        # Get existing issue IDs to avoid duplicates
        existing_issue_ids = set(
            self.reading_list.reading_list_items.values_list("issue_id", flat=True)
        )

        # Filter out issues already in the reading list
        new_issues = [issue for issue in issues_to_add if issue.pk not in existing_issue_ids]

        if not new_issues:
            messages.info(
                self.request,
                f"No new issues to add. All issues from {arc} are already in the list.",
            )
            return redirect(self.get_success_url())

        # Determine starting order based on position
        if position == "beginning":
            # Insert at the beginning - need to reorder existing items
            start_order = 1
            # Shift existing items down
            existing_items = self.reading_list.reading_list_items.order_by("order")
            for idx, item in enumerate(existing_items, start=len(new_issues) + 1):
                if item.order != idx:
                    item.order = idx
                    item.save()
        else:
            # Add at the end
            max_order = (
                self.reading_list.reading_list_items.aggregate(models.Max("order"))["order__max"]
                or 0
            )
            start_order = max_order + 1

        # Create reading list items for new issues
        items_to_create = [
            ReadingListItem(
                reading_list=self.reading_list,
                issue=issue,
                order=start_order + idx,
            )
            for idx, issue in enumerate(new_issues)
        ]

        ReadingListItem.objects.bulk_create(items_to_create)

        # Provide feedback
        position_text = "at the beginning" if position == "beginning" else "at the end"
        messages.success(
            self.request,
            f"Added {len(new_issues)} issue(s) from {arc} {position_text} "
            f"of '{self.reading_list.name}'!",
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reading_list"] = self.reading_list
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
        queryset = ReadingList.objects.all()

        # If not authenticated, only show public lists
        if not request.user.is_authenticated:
            queryset = queryset.filter(is_private=False)
        # If admin or reading list editor, show public lists + user's own lists + Metron's lists
        elif (
            request.user.is_staff or request.user.groups.filter(name="reading list editor").exists()
        ):
            try:
                metron_user = CustomUser.objects.get(username="Metron")
                queryset = queryset.filter(
                    Q(is_private=False) | Q(user=request.user) | Q(user=metron_user)
                )
            except CustomUser.DoesNotExist:
                queryset = queryset.filter(Q(is_private=False) | Q(user=request.user))
        # If authenticated, show public lists + user's own lists
        else:
            queryset = queryset.filter(Q(is_private=False) | Q(user=request.user))

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

    rating_value = request.POST.get("rating")
    if rating_value:
        try:
            rating = int(rating_value)
            if MIN_RATING <= rating <= MAX_RATING:
                # Update or create rating
                ReadingListRating.objects.update_or_create(
                    reading_list=reading_list,
                    user=request.user,
                    defaults={"rating": rating},
                )
            elif rating == 0:  # Allow clearing the rating
                ReadingListRating.objects.filter(
                    reading_list=reading_list,
                    user=request.user,
                ).delete()
        except ValueError:
            pass

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
        "reading_lists/partials/reading_list_rating.html",
        {
            "reading_list": reading_list,
            "user_rating": user_rating,
            "average_rating": avg_data["avg"],
            "rating_count": avg_data["count"],
        },
    )
