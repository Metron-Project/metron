import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from comicsdb.models.issue import Issue
from comicsdb.views.mixins import SearchMixin
from reading_lists.cbl_importer import CBLImportError, CBLParseError, import_cbl_file
from reading_lists.forms import AddIssueWithSearchForm, ImportCBLForm, ReadingListForm
from reading_lists.models import ReadingList, ReadingListItem
from users.models import CustomUser


class ReadingListListView(ListView):
    """Display all public reading lists, plus user's own lists if authenticated."""

    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        queryset = ReadingList.objects.select_related("user").annotate(issue_count=Count("issues"))

        if self.request.user.is_authenticated:
            # If admin, show public lists + user's own lists + Metron's lists
            if self.request.user.is_staff:
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

        return queryset


class SearchReadingListListView(SearchMixin, ReadingListListView):
    """Search reading lists by name, user, or attribution source."""

    def get_search_fields(self):
        """Search across name, username, and attribution source display text."""
        return ["name__icontains", "user__username__icontains", "attribution_source__icontains"]


class UserReadingListListView(LoginRequiredMixin, ListView):
    """Display only the current user's reading lists."""

    model = ReadingList
    template_name = "reading_lists/user_readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        return ReadingList.objects.filter(user=self.request.user).annotate(
            issue_count=Count("issues")
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

        # If admin, show public lists + user's own lists + Metron's lists
        if self.request.user.is_staff:
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

        # Get ordered issues
        context["reading_list_items"] = reading_list.reading_list_items.select_related(
            "issue__series__series_type"
        ).order_by("order")

        # Check if user is the owner OR admin viewing Metron's list
        is_actual_owner = (
            self.request.user.is_authenticated and reading_list.user == self.request.user
        )
        is_admin_managing_metron = (
            self.request.user.is_authenticated
            and self.request.user.is_staff
            and reading_list.user.username == "Metron"
        )
        context["is_owner"] = is_actual_owner or is_admin_managing_metron

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
        """Only allow the owner to edit the list, or admins for Metron's lists."""
        reading_list = self.get_object()
        is_owner = reading_list.user == self.request.user
        is_admin_managing_metron = (
            self.request.user.is_staff and reading_list.user.username == "Metron"
        )
        return is_owner or is_admin_managing_metron

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
        """Only allow the owner to delete the list, or admins for Metron's lists."""
        reading_list = self.get_object()
        is_owner = reading_list.user == self.request.user
        is_admin_managing_metron = (
            self.request.user.is_staff and reading_list.user.username == "Metron"
        )
        return is_owner or is_admin_managing_metron

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
        """Only allow the owner to remove issues, or admins for Metron's lists."""
        is_owner = self.reading_list.user == self.request.user
        is_admin_managing_metron = (
            self.request.user.is_staff and self.reading_list.user.username == "Metron"
        )
        return is_owner or is_admin_managing_metron

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
        """Only allow the owner to add issues, or admins for Metron's lists."""
        is_owner = self.reading_list.user == self.request.user
        is_admin_managing_metron = (
            self.request.user.is_staff and self.reading_list.user.username == "Metron"
        )
        return is_owner or is_admin_managing_metron

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


class ImportCBLView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Import a Comic Book List (.cbl) file to create a reading list."""

    form_class = ImportCBLForm
    template_name = "reading_lists/import_cbl.html"
    success_url = reverse_lazy("reading-list:my-lists")

    def test_func(self):
        """Only allow admin users to import CBL files."""
        return self.request.user.is_staff

    def form_valid(self, form):
        cbl_file = form.cleaned_data["cbl_file"]
        is_private = form.cleaned_data.get("is_private", False)
        attribution_source = form.cleaned_data.get("attribution_source", "")
        attribution_url = form.cleaned_data.get("attribution_url", "")

        # Get the Metron user for CBL imports
        try:
            metron_user = CustomUser.objects.get(username="Metron")
        except CustomUser.DoesNotExist:
            messages.error(
                self.request,
                "The 'Metron' user account does not exist. "
                "Please create this user account before importing CBL files.",
            )
            return self.form_invalid(form)

        # Save the uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".cbl", delete=False) as tmp_file:
            for chunk in cbl_file.chunks():
                tmp_file.write(chunk)
            tmp_path = Path(tmp_file.name)

        try:
            # Import the CBL file (assigned to Metron user)
            result = import_cbl_file(
                file_path=tmp_path,
                user=metron_user,
                is_private=is_private,
                attribution_source=attribution_source,
                attribution_url=attribution_url,
            )

            # Store result in session for display on success page
            self.request.session["cbl_import_result"] = {
                "reading_list_name": result.reading_list.name,
                "reading_list_slug": result.reading_list.slug,
                "issues_added": result.issues_added,
                "issues_not_found_count": len(result.issues_not_found),
                "issues_skipped_count": len(result.issues_skipped),
                "issues_not_found": [
                    {
                        "series": book.series,
                        "number": book.number,
                        "year": book.year,
                        "database": book.database_name.upper(),
                        "issue_id": book.database_issue_id,
                    }
                    for book in result.issues_not_found[:20]  # Limit to first 20
                ],
                "issues_skipped": [
                    {
                        "series": book.series,
                        "number": book.number,
                        "reason": reason,
                    }
                    for book, reason in result.issues_skipped[:20]  # Limit to first 20
                ],
            }

            # Success message
            msg = f"Successfully imported reading list '{result.reading_list.name}'"
            if result.issues_added > 0:
                msg += f" with {result.issues_added} issue(s)"
            messages.success(self.request, msg)

            # Warning messages for issues not found or skipped
            if result.issues_not_found:
                messages.warning(
                    self.request,
                    f"{len(result.issues_not_found)} issue(s) not found in database",
                )
            if result.issues_skipped:
                messages.info(
                    self.request,
                    f"{len(result.issues_skipped)} issue(s) skipped",
                )

            # Redirect to the import result page
            return redirect("reading-list:import-result")

        except CBLParseError as e:
            messages.error(self.request, f"Failed to parse CBL file: {e}")
            return self.form_invalid(form)

        except CBLImportError as e:
            messages.error(self.request, f"Failed to import CBL file: {e}")
            return self.form_invalid(form)

        except OSError as e:
            messages.error(self.request, f"File operation error: {e}")
            return self.form_invalid(form)

        finally:
            # Clean up the temporary file
            if tmp_path.exists():
                tmp_path.unlink()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Import Comic Book List"
        return context


class ImportCBLResultView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    """Display the results of a CBL import."""

    template_name = "reading_lists/import_cbl_result.html"
    form_class = ImportCBLForm  # Allows importing another file
    success_url = reverse_lazy("reading-list:import-result")

    def test_func(self):
        """Only allow admin users to view import results."""
        return self.request.user.is_staff

    def get(self, request, *args, **kwargs):
        # Get the result from the session
        self.import_result = request.session.get("cbl_import_result")
        if not self.import_result:
            messages.info(request, "No import result available")
            return redirect("reading-list:my-lists")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Handle importing another file (reuse the ImportCBLView logic)
        return ImportCBLView.as_view()(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["result"] = self.import_result
        context["title"] = "Import Results"
        return context
