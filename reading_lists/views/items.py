"""Views that add issues to, or remove them from, a reading list."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, ngettext
from django.views.generic import DeleteView, FormView

from comicsdb.models.issue import Issue
from comicsdb.views.issue_list_helpers import filter_issues_by_number_range
from reading_lists.forms import (
    AddIssuesFromArcForm,
    AddIssuesFromSeriesForm,
    AddIssueWithSearchForm,
)
from reading_lists.models import ReadingList, ReadingListItem
from reading_lists.services import add_issues_to_reading_list
from reading_lists.views.mixins import ManageReadingListMixin


class RemoveIssueFromReadingListView(
    ManageReadingListMixin, LoginRequiredMixin, UserPassesTestMixin, DeleteView
):
    """Remove an issue from a reading list."""

    model = ReadingListItem
    template_name = "reading_lists/remove_issue_confirm.html"

    def get_object(self):
        return get_object_or_404(
            ReadingListItem,
            reading_list=self.reading_list,
            pk=self.kwargs["item_pk"],
        )

    def get_success_url(self):
        messages.success(
            self.request,
            _("Removed %(issue)s from '%(name)s'!")
            % {"issue": self.object.issue, "name": self.reading_list.name},
        )
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})


class AddIssueWithAutocompleteView(
    ManageReadingListMixin, LoginRequiredMixin, UserPassesTestMixin, FormView
):
    """Add an issue to a reading list using autocomplete search."""

    form_class = AddIssueWithSearchForm
    template_name = "reading_lists/add_issue_autocomplete.html"

    def form_valid(self, form):
        new_issues = form.cleaned_data["issues"]
        # Already parsed into de-duplicated ints by the form (existing + new issue pks).
        issue_order = form.cleaned_data["issue_order"]

        # One query each for the list's items and the new issues, instead of per entry.
        items_by_issue = {
            item.issue_id: item for item in self.reading_list.reading_list_items.all()
        }
        new_issues_by_pk = {issue.pk: issue for issue in new_issues}
        if not issue_order:
            # Default to existing issues (in their current order) + new issues.
            existing = sorted(items_by_issue.values(), key=lambda item: item.order)
            issue_order = [item.issue_id for item in existing] + list(new_issues_by_pk)

        items_to_update = []
        items_to_create = []
        added_issues = []
        for new_order, issue_pk in enumerate(issue_order, start=1):
            if item := items_by_issue.get(issue_pk):
                if item.order != new_order:
                    item.order = new_order
                    items_to_update.append(item)
            elif issue := new_issues_by_pk.get(issue_pk):
                items_to_create.append(
                    ReadingListItem(reading_list=self.reading_list, issue=issue, order=new_order)
                )
                added_issues.append(str(issue))
            # Any other pk (not on the list and not being added) is ignored.

        with transaction.atomic():
            ReadingListItem.objects.bulk_update(items_to_update, ["order"])
            ReadingListItem.objects.bulk_create(items_to_create)
            if items_to_update or items_to_create:
                # Bulk writes skip the post_save signal that normally bumps this.
                ReadingList.objects.filter(pk=self.reading_list.pk).update(modified=timezone.now())
        self._report_changes(added_issues, len(items_to_update))
        return redirect(self.get_success_url())

    def _report_changes(self, added_issues, reordered_count):
        added_count = len(added_issues)
        # Provide feedback
        message_parts = []
        if added_count > 0:
            if added_count == 1:
                message_parts.append(_("Added %(issue)s") % {"issue": added_issues[0]})
            else:
                message_parts.append(
                    ngettext("Added %(count)d issue", "Added %(count)d issues", added_count)
                    % {"count": added_count}
                )

        if reordered_count > 0:
            message_parts.append(
                ngettext(
                    "reordered %(count)d existing issue",
                    "reordered %(count)d existing issues",
                    reordered_count,
                )
                % {"count": reordered_count}
            )

        if message_parts:
            if len(message_parts) > 1:
                summary = _("%(first)s and %(second)s") % {
                    "first": message_parts[0],
                    "second": message_parts[1],
                }
            else:
                summary = message_parts[0]
            messages.success(
                self.request,
                _("%(summary)s in '%(name)s'!")
                % {"summary": summary, "name": self.reading_list.name},
            )

        if added_count == 0 and reordered_count == 0:
            messages.info(self.request, _("No changes were made."))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get existing issues in the reading list
        context["existing_items"] = self.reading_list.reading_list_items.select_related(
            "issue__series__series_type"
        ).order_by("order")
        return context


class AddIssuesFromSeriesView(
    ManageReadingListMixin, LoginRequiredMixin, UserPassesTestMixin, FormView
):
    """Add multiple issues from a series to a reading list."""

    form_class = AddIssuesFromSeriesForm
    template_name = "reading_lists/add_issues_from_series.html"

    def form_valid(self, form):
        series = form.cleaned_data["series"]
        range_type = form.cleaned_data["range_type"]
        start_number = form.cleaned_data.get("start_number")
        end_number = form.cleaned_data.get("end_number")
        position = form.cleaned_data["position"]

        # Get all issues from the series, ordered by cover date
        issues_queryset = Issue.objects.filter(series=series).order_by("cover_date", "number")
        if range_type == "range":
            issues_to_add = filter_issues_by_number_range(issues_queryset, start_number, end_number)
        else:
            issues_to_add = list(issues_queryset)

        added_count = add_issues_to_reading_list(self.reading_list, issues_to_add, position)

        if added_count == 0:
            messages.info(
                self.request,
                _("No new issues to add. All issues from %(series)s are already in the list.")
                % {"series": series},
            )
            return redirect(self.get_success_url())

        if position == "beginning":
            message = ngettext(
                "Added %(count)d issue from %(series)s at the beginning of '%(name)s'!",
                "Added %(count)d issues from %(series)s at the beginning of '%(name)s'!",
                added_count,
            )
        else:
            message = ngettext(
                "Added %(count)d issue from %(series)s at the end of '%(name)s'!",
                "Added %(count)d issues from %(series)s at the end of '%(name)s'!",
                added_count,
            )
        messages.success(
            self.request,
            message % {"count": added_count, "series": series, "name": self.reading_list.name},
        )

        return redirect(self.get_success_url())


class AddIssuesFromArcView(
    ManageReadingListMixin, LoginRequiredMixin, UserPassesTestMixin, FormView
):
    """Add all issues from a story arc to a reading list."""

    form_class = AddIssuesFromArcForm
    template_name = "reading_lists/add_issues_from_arc.html"

    def form_valid(self, form):
        arc = form.cleaned_data["arc"]
        position = form.cleaned_data["position"]

        issues_to_add = list(arc.issues.order_by("cover_date", "number"))
        added_count = add_issues_to_reading_list(self.reading_list, issues_to_add, position)

        if added_count == 0:
            messages.info(
                self.request,
                _("No new issues to add. All issues from %(arc)s are already in the list.")
                % {"arc": arc},
            )
            return redirect(self.get_success_url())

        if position == "beginning":
            message = ngettext(
                "Added %(count)d issue from %(arc)s at the beginning of '%(name)s'!",
                "Added %(count)d issues from %(arc)s at the beginning of '%(name)s'!",
                added_count,
            )
        else:
            message = ngettext(
                "Added %(count)d issue from %(arc)s at the end of '%(name)s'!",
                "Added %(count)d issues from %(arc)s at the end of '%(name)s'!",
                added_count,
            )
        messages.success(
            self.request,
            message % {"count": added_count, "arc": arc, "name": self.reading_list.name},
        )

        return redirect(self.get_success_url())
