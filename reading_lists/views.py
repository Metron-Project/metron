from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import models
from django.db.models import Avg, Count, Prefetch
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from comicsdb.filters.reading_list import ReadingListViewFilter
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Credits, Role
from comicsdb.models.issue import Issue
from comicsdb.views.mixins import LazyLoadMixin, SearchMixin
from reading_lists.forms import (
    AddIssuesFromArcForm,
    AddIssuesFromSeriesForm,
    AddIssueWithSearchForm,
    ReadingListForm,
)
from reading_lists.models import (
    READING_LIST_EDITOR_GROUP,
    ReadingList,
    ReadingListItem,
    ReadingListRating,
)
from users.models import CustomUser

# Pagination constant for reading list detail view
READING_LIST_DETAIL_PAGINATE_BY = 50

# Rating constants
MIN_RATING = 1
MAX_RATING = 5

_NON_FILTER_PARAMS = {"page"}

_FILTER_LABELS = {
    "q": "Search",
    "name": "Name",
    "username": "Creator",
    "publisher": "Publisher",
    "list_type": "List Type",
    "attribution_source": "Attribution",
    "average_rating__gte": "Min Rating",
    "is_private": "Privacy",
}

_RATING_DISPLAY = {
    "1": "1+ Stars",
    "2": "2+ Stars",
    "3": "3+ Stars",
    "4": "4+ Stars",
    "5": "5 Stars",
}

_PRIVACY_DISPLAY = {"true": "Private", "false": "Public"}

_ISSUE_TYPE_META = {
    "CORE": ("Core", "#3273dc"),
    "TIE_IN": ("Tie-In", "#f5b400"),
    "PROLOGUE": ("Prologue", "#3e8ed0"),
    "EPILOGUE": ("Epilogue", "#48c78e"),
}

_CREDIT_ROLE_NAMES = ["Artist", "Finishes", "Inker", "Penciller", "Script", "Story", "Writer"]

_CREDIT_ROLE_DISPLAY = {
    "Artist": "Artist",
    "Finishes": "Artist",
    "Inker": "Artist",
    "Penciller": "Artist",
    "Script": "Writer",
    "Story": "Writer",
    "Writer": "Writer",
}


def build_active_filters(request):
    """Build a list of ``{label, value, remove_url}`` dicts for the chip bar."""
    get = request.GET
    list_type_names = dict(ReadingList.ListType.choices)
    attribution_names = dict(ReadingList.AttributionSource.choices)

    chips = []
    for key in get:
        if key in _NON_FILTER_PARAMS:
            continue
        value = get.get(key)
        if not value:
            continue

        if key == "list_type":
            display = list_type_names.get(value, value)
        elif key == "attribution_source":
            display = attribution_names.get(value, value)
        elif key == "average_rating__gte":
            display = _RATING_DISPLAY.get(value, value)
        elif key == "is_private":
            display = _PRIVACY_DISPLAY.get(value, value)
        else:
            display = value

        kept = [(k, v) for k, v in get.items() if k not in (key, "page")]
        remove_url = f"?{urlencode(kept)}" if kept else "?"

        chips.append(
            {
                "label": _FILTER_LABELS.get(key, key.replace("_", " ").title()),
                "value": display,
                "remove_url": remove_url,
            }
        )
    return chips


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
        is_editor_group = user.groups.filter(name=READING_LIST_EDITOR_GROUP).exists()
        return is_owner or is_staff or is_editor_group

    return is_owner


def can_assign_reading_list_to_metron(user):
    """Check if a user can reassign a reading list's owner to the Metron account.

    Allowed for staff or members of the 'reading list editor' group.
    """
    return user.is_staff or user.groups.filter(name=READING_LIST_EDITOR_GROUP).exists()


def filter_issues_by_number_range(issues, start_number, end_number):
    """Restrict an ordered iterable of issues to the inclusive range of issue numbers.

    Either bound may be omitted to mean "from the beginning" / "through the end".
    Matching is by ``Issue.number`` string equality, in the given iteration order.
    """
    if not start_number and not end_number:
        return list(issues)

    filtered = []
    in_range = not start_number
    for issue in issues:
        if start_number and issue.number == start_number:
            in_range = True
        if in_range:
            filtered.append(issue)
        if end_number and issue.number == end_number:
            break
    return filtered


def add_issues_to_reading_list(reading_list, candidate_issues, position):
    """Add issues not already in the list, ordered at the beginning or end.

    Existing items are shifted down when inserting at the beginning; otherwise
    new issues are appended after the current maximum order. Returns the number
    of issues actually added (issues already in the list are skipped).
    """
    existing_issue_ids = set(reading_list.reading_list_items.values_list("issue_id", flat=True))
    new_issues = [issue for issue in candidate_issues if issue.pk not in existing_issue_ids]

    if not new_issues:
        return 0

    if position == "beginning":
        start_order = 1
        existing_items = reading_list.reading_list_items.order_by("order")
        for idx, item in enumerate(existing_items, start=len(new_issues) + 1):
            if item.order != idx:
                item.order = idx
                item.save()
    else:
        max_order = (
            reading_list.reading_list_items.aggregate(models.Max("order"))["order__max"] or 0
        )
        start_order = max_order + 1

    ReadingListItem.objects.bulk_create(
        ReadingListItem(reading_list=reading_list, issue=issue, order=start_order + idx)
        for idx, issue in enumerate(new_issues)
    )
    return len(new_issues)


class ReadingListFromSlugMixin:
    """Fetch the parent ReadingList named by the ``slug`` URL kwarg into ``self.reading_list``.

    Must precede auth mixins (``LoginRequiredMixin``, ``UserPassesTestMixin``) in the
    base class list so ``self.reading_list`` is set before ``UserPassesTestMixin``
    calls ``test_func()``.
    """

    def dispatch(self, request, *args, **kwargs):
        self.reading_list = get_object_or_404(ReadingList, slug=kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)


class ManageReadingListMixin(ReadingListFromSlugMixin):
    """Restrict access to users who can manage ``self.reading_list``, and expose it."""

    def test_func(self):
        return can_manage_reading_list(self.request.user, self.reading_list)

    def get_success_url(self):
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["reading_list"] = self.reading_list
        return context


class ReadingListListView(ListView):
    """Display all public reading lists, plus user's own lists if authenticated."""

    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        queryset = (
            ReadingList.objects.select_related("user")
            .with_list_stats()
            .visible_to(self.request.user)
            .distinct()
        )

        # Apply filters
        filtered = ReadingListViewFilter(self.request.GET, queryset=queryset)
        return filtered.qs.distinct().order_by("name", "attribution_source", "user")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["attribution_sources"] = ReadingList.AttributionSource.choices
        context["list_types"] = ReadingList.ListType.choices
        context["has_active_filters"] = any(key != "page" for key in self.request.GET)
        context["active_filters"] = build_active_filters(self.request)
        return context


class SearchReadingListListView(SearchMixin, ReadingListListView):
    """Search reading lists by name, user, or attribution source."""

    def get_search_fields(self):
        """Search across name, username, and attribution source display text."""
        return ["name__icontains", "user__username__icontains", "attribution_source__icontains"]

    def get_queryset(self):
        """Get queryset without applying the filter (SearchMixin handles search)."""
        queryset = (
            ReadingList.objects.select_related("user")
            .with_list_stats()
            .visible_to(self.request.user)
            .distinct()
        )

        # Apply SearchMixin search logic (not the filter)
        if query := self.request.GET.get("q"):
            queryset = self.get_search_queryset(queryset, query)

        return queryset.order_by("name", "attribution_source", "user")


class UserReadingListListView(LoginRequiredMixin, ListView):
    """Display only the current user's reading lists."""

    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_user_view"] = True
        return context

    def get_queryset(self):
        return (
            ReadingList.objects.filter(user=self.request.user)
            .with_list_stats()
            .order_by("name", "attribution_source", "user")
        )


def build_reading_list_breakdown_context(reading_list_items):
    """Compute issue-type/series/publisher breakdowns and featured creators/characters.

    ``reading_list_items`` must be a non-empty, pre-fetched sequence of
    ReadingListItem rows (as built by ReadingListDetailView.get_queryset).
    """
    type_counts = {}
    series_counts = {}
    publisher_counts = {}

    for item in reading_list_items:
        key = item.issue_type or ""
        if key:
            type_counts[key] = type_counts.get(key, 0) + 1

        series = item.issue.series
        s_entry = series_counts.setdefault(series.id, {"series": series, "count": 0})
        s_entry["count"] += 1

        publisher = series.publisher
        if publisher:
            p_entry = publisher_counts.setdefault(
                publisher.id, {"publisher": publisher, "count": 0}
            )
            p_entry["count"] += 1

    issue_type_breakdown = [
        {
            "key": k,
            "label": _ISSUE_TYPE_META[k][0],
            "color": _ISSUE_TYPE_META[k][1],
            "count": type_counts[k],
        }
        for k in ("CORE", "TIE_IN", "PROLOGUE", "EPILOGUE")
        if type_counts.get(k)
    ]

    series_breakdown = sorted(
        series_counts.values(),
        key=lambda e: (-e["count"], e["series"].name),
    )
    publisher_breakdown = sorted(
        publisher_counts.values(),
        key=lambda e: (-e["count"], e["publisher"].name),
    )

    issue_ids = [item.issue_id for item in reading_list_items]
    top6 = list(
        Creator.objects.filter(
            credits__issue_id__in=issue_ids,
            credits__role__name__in=_CREDIT_ROLE_NAMES,
        )
        .annotate(issue_count=Count("credits__issue", distinct=True))
        .order_by("-issue_count", "name")[:6]
    )
    creator_ids = [c.id for c in top6]
    role_map: dict[int, set[str]] = {}
    for credit in Credits.objects.filter(
        issue_id__in=issue_ids,
        creator_id__in=creator_ids,
        role__name__in=_CREDIT_ROLE_NAMES,
    ).prefetch_related(Prefetch("role", queryset=Role.objects.filter(name__in=_CREDIT_ROLE_NAMES))):
        for role in credit.role.all():
            role_map.setdefault(credit.creator_id, set()).add(role.name)

    featured_creators = [
        {
            "creator": c,
            "roles": ", ".join(
                sorted({_CREDIT_ROLE_DISPLAY.get(r, r) for r in role_map.get(c.id, [])})
            ),
        }
        for c in top6
    ]

    top_characters = (
        Character.objects.filter(issues__in=issue_ids)
        .annotate(appearance_count=Count("issues", distinct=True))
        .order_by("-appearance_count", "name")[:12]
    )

    return {
        "issue_type_breakdown": issue_type_breakdown,
        "series_breakdown": series_breakdown,
        "publisher_breakdown": publisher_breakdown,
        "featured_creators": featured_creators,
        "top_characters": top_characters,
    }


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
            .with_list_stats()
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

        return queryset.visible_to(self.request.user)

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
            context["can_assign_to_metron"] = reading_list.user.username != "Metron" and (
                can_assign_reading_list_to_metron(self.request.user)
            )
        else:
            context["is_owner"] = False
            context["can_assign_to_metron"] = False

        # Get user's rating from prefetched data
        user_rating = None
        if self.request.user.is_authenticated:
            user_rating_list = getattr(reading_list, "user_rating_list", [])
            user_rating = user_rating_list[0] if user_rating_list else None

        # Use annotated average rating (already calculated in get_queryset)
        context["user_rating"] = user_rating
        context["average_rating"] = reading_list.average_rating
        context["rating_count"] = reading_list.rating_count

        # Add annotated year data to context
        context["start_year"] = reading_list.start_year_annotated
        context["end_year"] = reading_list.end_year_annotated

        # Add issue-type/series/publisher breakdowns and featured creators/characters
        if reading_list_items_count > 0:
            context.update(build_reading_list_breakdown_context(reading_list_items))

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


class AssignReadingListToMetronView(
    ReadingListFromSlugMixin, LoginRequiredMixin, UserPassesTestMixin, View
):
    """Reassign a reading list's owner to the Metron account."""

    def test_func(self):
        """Only allow staff or 'reading list editor' group members."""
        return can_assign_reading_list_to_metron(self.request.user)

    def get(self, request, *args, **kwargs):
        if self.reading_list.user.username == "Metron":
            return redirect(self.reading_list.get_absolute_url())
        return render(
            request,
            "reading_lists/readinglist_confirm_assign_metron.html",
            {"reading_list": self.reading_list},
        )

    def post(self, request, *args, **kwargs):
        try:
            metron_user = CustomUser.objects.get(username="Metron")
        except CustomUser.DoesNotExist:
            messages.error(request, "The 'Metron' user account does not exist.")
            return redirect(self.reading_list.get_absolute_url())

        if self.reading_list.user_id != metron_user.id:
            self.reading_list.user = metron_user
            self.reading_list.save()
            messages.success(
                request,
                f"Ownership of '{self.reading_list.name}' has been reassigned to Metron.",
            )
        return redirect(self.reading_list.get_absolute_url())


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
            f"Removed {self.object.issue} from '{self.reading_list.name}'!",
        )
        return reverse("reading-list:detail", kwargs={"slug": self.reading_list.slug})


class AddIssueWithAutocompleteView(
    ManageReadingListMixin, LoginRequiredMixin, UserPassesTestMixin, FormView
):
    """Add an issue to a reading list using autocomplete search."""

    form_class = AddIssueWithSearchForm
    template_name = "reading_lists/add_issue_autocomplete.html"

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
                f"No new issues to add. All issues from {series} are already in the list.",
            )
            return redirect(self.get_success_url())

        position_text = "at the beginning" if position == "beginning" else "at the end"
        messages.success(
            self.request,
            f"Added {added_count} issue(s) from {series} {position_text} "
            f"of '{self.reading_list.name}'!",
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
                f"No new issues to add. All issues from {arc} are already in the list.",
            )
            return redirect(self.get_success_url())

        position_text = "at the beginning" if position == "beginning" else "at the end"
        messages.success(
            self.request,
            f"Added {added_count} issue(s) from {arc} {position_text} "
            f"of '{self.reading_list.name}'!",
        )

        return redirect(self.get_success_url())


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
        queryset = ReadingList.objects.visible_to(request.user)

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


@login_required
def edit_issue_type(request, slug, item_pk):
    """HTMX view to show the edit form for issue type."""
    reading_list = get_object_or_404(ReadingList, slug=slug)

    # Check if user can manage this reading list
    if not can_manage_reading_list(request.user, reading_list):
        return HttpResponseForbidden("You do not have permission to edit this reading list")

    # Get the reading list item
    item = get_object_or_404(
        ReadingListItem,
        reading_list=reading_list,
        pk=item_pk,
    )

    # Return the edit form
    return render(
        request,
        "reading_lists/partials/readinglist_item_edit.html",
        {
            "item": item,
            "reading_list_slug": slug,
        },
    )


@login_required
@require_POST
def update_issue_type(request, slug, item_pk):
    """HTMX view to update the issue type of a reading list item."""
    reading_list = get_object_or_404(ReadingList, slug=slug)

    # Check if user can manage this reading list
    if not can_manage_reading_list(request.user, reading_list):
        return HttpResponseForbidden("You do not have permission to edit this reading list")

    # Get the reading list item
    item = get_object_or_404(
        ReadingListItem,
        reading_list=reading_list,
        pk=item_pk,
    )

    # Update the issue type
    issue_type = request.POST.get("issue_type", "")
    if issue_type in dict(ReadingListItem.IssueType.choices) or issue_type == "":
        item.issue_type = issue_type
        item.save()

    # Return the updated item display
    return render(
        request,
        "reading_lists/partials/readinglist_item.html",
        {
            "item": item,
            "reading_list_slug": slug,
            "is_owner": True,
        },
    )


@login_required
def cancel_edit_issue_type(request, slug, item_pk):
    """HTMX view to cancel editing and return to display mode."""
    reading_list = get_object_or_404(ReadingList, slug=slug)

    # Check if user can manage this reading list
    if not can_manage_reading_list(request.user, reading_list):
        return HttpResponseForbidden("You do not have permission to edit this reading list")

    # Get the reading list item
    item = get_object_or_404(
        ReadingListItem,
        reading_list=reading_list,
        pk=item_pk,
    )

    # Return the display view
    return render(
        request,
        "reading_lists/partials/readinglist_item.html",
        {
            "item": item,
            "reading_list_slug": slug,
            "is_owner": True,
        },
    )
