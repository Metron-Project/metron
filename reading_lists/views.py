from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from comicsdb.models.issue import Issue
from reading_lists.forms import AddIssueWithSearchForm, ReadingListForm
from reading_lists.models import ReadingList, ReadingListItem


class ReadingListListView(ListView):
    """Display all public reading lists, plus user's own lists if authenticated."""

    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        queryset = ReadingList.objects.select_related("user").annotate(issue_count=Count("issues"))

        if self.request.user.is_authenticated:
            # Show public lists + user's own lists (including private)
            queryset = queryset.filter(Q(is_private=False) | Q(user=self.request.user)).distinct()
        else:
            # Show only public lists
            queryset = queryset.filter(is_private=False)

        return queryset.order_by("-modified")


class UserReadingListListView(LoginRequiredMixin, ListView):
    """Display only the current user's reading lists."""

    model = ReadingList
    template_name = "reading_lists/user_readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        return (
            ReadingList.objects.filter(user=self.request.user)
            .annotate(issue_count=Count("issues"))
            .order_by("-modified")
        )


class ReadingListDetailView(DetailView):
    """Display a single reading list with its issues."""

    model = ReadingList
    template_name = "reading_lists/readinglist_detail.html"
    context_object_name = "reading_list"

    def get_queryset(self):
        queryset = ReadingList.objects.select_related("user").prefetch_related(
            "reading_list_items__issue__series__series_type"
        )

        # If not authenticated, only show public lists
        if not self.request.user.is_authenticated:
            return queryset.filter(is_private=False)

        # If authenticated, show public lists + user's own lists
        return queryset.filter(Q(is_private=False) | Q(user=self.request.user))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reading_list = context["reading_list"]

        # Get ordered issues
        context["reading_list_items"] = reading_list.reading_list_items.select_related(
            "issue__series__series_type"
        ).order_by("order", "created_on")

        # Check if user is the owner
        context["is_owner"] = (
            self.request.user.is_authenticated and reading_list.user == self.request.user
        )

        return context


class ReadingListCreateView(LoginRequiredMixin, CreateView):
    """Create a new reading list."""

    model = ReadingList
    form_class = ReadingListForm
    template_name = "reading_lists/readinglist_form.html"

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
        """Only allow the owner to edit the list."""
        reading_list = self.get_object()
        return reading_list.user == self.request.user

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
        """Only allow the owner to delete the list."""
        reading_list = self.get_object()
        return reading_list.user == self.request.user

    def form_valid(self, form):
        messages.success(self.request, f"Reading list '{self.object.name}' deleted!")
        return super().form_valid(form)


class AddIssueToReadingListView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Add an issue to a reading list."""

    model = ReadingListItem
    fields = ["order"]
    template_name = "reading_lists/add_issue.html"

    def dispatch(self, request, *args, **kwargs):
        # Get the reading list and issue
        self.reading_list = get_object_or_404(ReadingList, slug=kwargs["slug"])
        self.issue = get_object_or_404(Issue, slug=kwargs["issue_slug"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Only allow the owner to add issues."""
        return self.reading_list.user == self.request.user

    def form_valid(self, form):
        # Check if issue is already in the list
        if ReadingListItem.objects.filter(
            reading_list=self.reading_list, issue=self.issue
        ).exists():
            messages.warning(
                self.request,
                f"{self.issue} is already in '{self.reading_list.name}'!",
            )
            return redirect(self.get_success_url())

        form.instance.reading_list = self.reading_list
        form.instance.issue = self.issue

        # If no order specified, add to the end
        if not form.instance.order:
            max_order = ReadingListItem.objects.filter(reading_list=self.reading_list).aggregate(
                max_order=Count("id")
            )["max_order"]
            form.instance.order = (max_order or 0) + 1

        messages.success(self.request, f"Added {self.issue} to '{self.reading_list.name}'!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reading_list"] = self.reading_list
        context["issue"] = self.issue
        return context


class RemoveIssueFromReadingListView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Remove an issue from a reading list."""

    model = ReadingListItem
    template_name = "reading_lists/remove_issue_confirm.html"

    def dispatch(self, request, *args, **kwargs):
        self.reading_list = get_object_or_404(ReadingList, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Only allow the owner to remove issues."""
        return self.reading_list.user == self.request.user

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
        """Only allow the owner to add issues."""
        return self.reading_list.user == self.request.user

    def form_valid(self, form):  # noqa: PLR0912
        new_issues = form.cleaned_data["issues"]
        issue_order_str = form.cleaned_data.get("issue_order", "")

        # Parse the issue order (contains both existing and new issue IDs)
        if issue_order_str:
            issue_order = [int(pk) for pk in issue_order_str.split(",") if pk.strip()]
        else:
            # Default to existing issues + new issues
            existing_items = self.reading_list.reading_list_items.order_by("order", "created_on")
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
        ).order_by("order", "created_on")
        return context
