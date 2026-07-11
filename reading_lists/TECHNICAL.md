# Reading Lists - Technical Documentation

Developer documentation for the `reading_lists` Django app.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Models](#models)
- [Views and URLs](#views-and-urls)
- [Forms](#forms)
- [Permissions](#permissions)
- [Autocomplete](#autocomplete)
- [Filters](#filters)
- [Templates](#templates)
- [Database Optimization](#database-optimization)
- [Dependencies](#dependencies)
- [Management Commands](#management-commands)
- [API Integration](#api-integration)
- [Testing](#testing)
- [Future Enhancements](#future-enhancements)

## Architecture Overview

The reading_lists app follows Django's MTV (Model-Template-View) pattern with:

- **Models**: `ReadingList`, `ReadingListItem` (through model), and `ReadingListRating`
- **Views**: Class-based views (CBVs) for most operations, plus several HTMX-powered function-based views
- **Forms**: Django forms with autocomplete integration
- **Permissions**: Shared helper functions (`can_manage_reading_list()`, `can_assign_reading_list_to_metron()`) used from `UserPassesTestMixin.test_func()` and from function-based views
- **Filters**: `django-filter` FilterSets for both the API (`ReadingListFilter`) and the web UI (`ReadingListViewFilter`)

**Key Dependencies:**

- Django's class-based views
- `autocomplete` package for issue, series, and arc search
- `django-filter` for API and web filtering
- `sorl-thumbnail` for cover image resizing
- `comicsdb` app for Issue, Publisher, Character, Creator, Credits, and Role models
- `users` app for CustomUser model

## Models

### ReadingList

The main model for user-created reading lists.

**File:** `reading_lists/models.py`

```python
class ReadingList(CommonInfo):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="reading_lists")
    is_private = models.BooleanField(default=False)
    list_type = models.CharField(max_length=10, choices=ListType.choices, default=ListType.EVENT)
    attribution_source = models.CharField(max_length=10, choices=AttributionSource.choices, blank=True)
    attribution_url = models.URLField(blank=True)
    image = ImageField(upload_to="reading_list/%Y/%m/%d/", blank=True)
    issues = models.ManyToManyField(
        Issue, through="ReadingListItem", related_name="in_reading_lists", blank=True
    )
```

Cover images use `sorl.thumbnail.ImageField` (same pattern as issue covers) and are optional.

**Inherited Fields from CommonInfo:**

- `name`: CharField with max_length from CommonInfo
- `slug`: Auto-generated from name via pre_save signal
- `desc`: TextField for description
- `cv_id`: ComicVine ID (optional)
- `gcd_id`: Grand Comics Database ID (optional)
- `created_on`: Auto-generated creation timestamp
- `modified`: Auto-updated modification timestamp

**List Types:**

```python
class ListType(models.TextChoices):
    CREATOR = "CREATOR", "Creator"
    EVENT = "EVENT", "Event"
    STORY = "STORY", "Story"
    CHARACTERS = "CHARACTERS", "Characters"
    TEAMS = "TEAMS", "Teams"
    MASTER = "MASTER", "Master"
```

Default is `EVENT`. Used for filtering/browsing and displayed as a tag on the list card.

**Attribution Sources:**

```python
class AttributionSource(models.TextChoices):
    CBRO = "CBRO", "Comic Book Reading Orders"
    CMRO = "CMRO", "Complete Marvel Reading Orders"
    CBH = "CBH", "Comic Book Herald"
    CBT = "CBT", "Comic Book Treasury"
    MG = "MG", "Marvel Guides"
    HTLC = "HTLC", "How To Love Comics"
    LOCG = "LOCG", "League of ComicGeeks"
    OTHER = "OTHER", "Other"
```

**Meta Options:**

```python
class Meta:
    ordering = ["name", "attribution_source", "user"]
    unique_together = ["user", "name", "attribution_source"]
```

**Constraints:**

- Unique together: `(user, name, attribution_source)` - a user can reuse a list name across different attribution sources, but not within the same one
- Index: Standard indexes on ForeignKey and slug fields

**Computed Properties:**

```python
@property
def start_year(self) -> int | None:
    """Get the earliest year from the reading list's issues."""
    earliest_issue = (
        self.reading_list_items.select_related("issue")
        .order_by("issue__cover_date")
        .first()
    )
    return earliest_issue.issue.cover_date.year if earliest_issue else None

@property
def end_year(self) -> int | None:
    """Get the latest year from the reading list's issues."""
    latest_issue = (
        self.reading_list_items.select_related("issue")
        .order_by("-issue__cover_date")
        .first()
    )
    return latest_issue.issue.cover_date.year if latest_issue else None

@property
def publishers(self):
    """Get all unique publishers from the reading list's issues."""
    return (
        Publisher.objects.filter(series__issues__reading_list_items__reading_list=self)
        .distinct()
        .order_by("name")
    )
```

**Methods:**

- `get_absolute_url()`: Returns detail view URL using slug
- `__str__()`: Returns formatted string with username, name, and attribution

### ReadingListItem

Through model for the M2M relationship between ReadingList and Issue.

```python
class ReadingListItem(models.Model):
    class IssueType(models.TextChoices):
        """Issue type choices for reading list items."""
        PROLOGUE = "PROLOGUE", "Prologue"
        CORE = "CORE", "Core Issue"
        TIE_IN = "TIE_IN", "Tie-In"
        EPILOGUE = "EPILOGUE", "Epilogue"

    reading_list = models.ForeignKey(
        ReadingList, on_delete=models.CASCADE, related_name="reading_list_items"
    )
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="reading_list_items")
    order = models.PositiveIntegerField(
        default=1, help_text="Position of this issue in the reading list"
    )
    issue_type = models.CharField(
        max_length=10,
        choices=IssueType.choices,
        blank=True,
        help_text="Optional categorization of this issue's role in the reading list",
    )
```

`order` is 1-indexed (migrations `0008_fix_order_default.py` and `0009_renumber_order_from_zero.py` moved the default and existing data from a 0-based scheme to a 1-based one, since 0-based ordering caused ambiguity with "unset" values).

**Issue Type Categorization:**

The `issue_type` field allows users to categorize issues within their reading lists to indicate their narrative role:

- **PROLOGUE**: Setup or prelude issues
- **CORE**: Main storyline issues
- **TIE_IN**: Related supplementary issues
- **EPILOGUE**: Conclusion or aftermath issues
- **Blank**: Uncategorized (default)

**Features:**

- Optional field (blank=True)
- Uses Django's TextChoices for type safety
- Displayed as badges in the web UI
- Exposed in API serializer
- Inline HTMX-based editing

**Migration:** `0004_readinglistitem_issue_type.py`

**Constraints:**

- Unique together: `(reading_list, issue)` - prevents duplicate issues
- Index: `(reading_list, order)` - optimizes ordering queries

**Meta Options:**

```python
class Meta:
    ordering = ["reading_list", "order"]
    indexes = [
        models.Index(fields=["reading_list", "order"], name="reading_list_order_idx"),
    ]
```

**Modified Timestamp Signal:**

**File:** `reading_lists/signals.py` (connected in `reading_lists/apps.py::ReadingListsConfig.ready()`)

```python
def update_reading_list_modified_on_item_change(sender, instance, **kwargs):
    ReadingList.objects.filter(pk=instance.reading_list_id).update(modified=timezone.now())
```

Connected to `post_save` and `post_delete` on `ReadingListItem` so that adding, reordering, or removing issues bumps the parent `ReadingList.modified` timestamp — important for the API's `modified_gt` filter and conditional-request support, since M2M/through-model changes don't otherwise touch the parent row's `auto_now` field.

### ReadingListRating

Model for community ratings of public reading lists.

**File:** `reading_lists/models.py`

```python
class ReadingListRating(models.Model):
    reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE, related_name="ratings")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="reading_list_ratings")
    rating = models.PositiveSmallIntegerField(
        choices=[(i, str(i)) for i in range(1, 6)],
        help_text="Star rating (1-5) for this reading list",
    )
    created_on = models.DateTimeField(db_default=models.functions.Now())
    modified = models.DateTimeField(auto_now=True)
```

**Features:**

- **1-5 Star Rating System**: Simple, universally understood rating scale
- **One Rating Per User**: Unique constraint prevents duplicate ratings
- **Timestamps**: Tracks when ratings are created and modified
- **Related Names**: Easy access via `reading_list.ratings` and `user.reading_list_ratings`

**Constraints:**

- Unique together: `(reading_list, user)` - one rating per user per list
- Index: `(reading_list, user)` - optimizes rating lookups

**Meta Options:**

```python
class Meta:
    unique_together = ["reading_list", "user"]
    indexes = [
        models.Index(fields=["reading_list", "user"]),
    ]
```

**Business Rules:**

- Users can only rate public reading lists
- Users cannot rate their own reading lists
- Ratings can be updated (users can change their rating)
- Ratings can be deleted (users can clear their rating)

**Migration:** `0003_readinglistrating.py`

## Views and URLs

Most views are class-based views (CBVs) inheriting from Django's generic views; several inline-editing/HTMX endpoints are plain function-based views decorated with `@login_required`/`@require_POST`.

**File:** `reading_lists/views.py`

### Permission Helpers

```python
def can_manage_reading_list(user, reading_list):
    """Owner, or staff/'reading list editor' group member editing a Metron list."""
    is_owner = reading_list.user == user
    if reading_list.user.username == "Metron":
        is_staff = user.is_staff
        is_editor_group = user.groups.filter(name="reading list editor").exists()
        return is_owner or is_staff or is_editor_group
    return is_owner


def can_assign_reading_list_to_metron(user):
    """Staff or 'reading list editor' group members, regardless of ownership."""
    return user.is_staff or user.groups.filter(name="reading list editor").exists()
```

Nearly every authenticated view/endpoint below delegates its `test_func()`/permission check to one of these two functions rather than duplicating the group/ownership logic. See [Permissions](#permissions) for the full breakdown.

### Public Views

#### ReadingListListView

```python
class ReadingListListView(ListView):
    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30
```

**Queryset Logic:**

- Unauthenticated: Only public lists
- Authenticated, staff or "reading list editor" group: Public lists + user's own lists + Metron's lists
- Authenticated, everyone else: Public lists + user's own lists

**Annotations:**

- `issue_count`: `Count("issues", distinct=True)`
- `average_rating`: `Avg("ratings__rating")`
- `rating_count`: `Count("ratings", distinct=True)`
- `start_year_annotated` / `end_year_annotated`: `Min`/`Max` of `reading_list_items__issue__cover_date__year`, used by the list card to show a year range without per-row queries

**Filtering:** Queryset is passed through `ReadingListViewFilter` (see [Filters](#filters)) before final ordering by `name, attribution_source, user`.

**Context Data:**

- `attribution_sources`, `list_types`: Choice lists for the filter form dropdowns
- `has_active_filters`: True if any GET param besides `page` is present
- `active_filters`: List of `{label, value, remove_url}` dicts built by `build_active_filters()`, powering the removable filter-chip bar above the results

**URL:** `/reading-lists/`

#### SearchReadingListListView

```python
class SearchReadingListListView(SearchMixin, ReadingListListView):
    def get_search_fields(self):
        return ["name__icontains", "user__username__icontains", "attribution_source__icontains"]
```

Reimplements `get_queryset()` (rather than fully inheriting it) so that `q` is applied via `SearchMixin.get_search_queryset()` instead of through `ReadingListViewFilter` — the same visibility rules (public/own/Metron) are still applied first.

**URL:** `/reading-lists/search/`

#### ReadingListDetailView

```python
class ReadingListDetailView(DetailView):
    model = ReadingList
    template_name = "reading_lists/readinglist_detail.html"
    context_object_name = "reading_list"
```

**Context Data:**

- `reading_list_items`: Prefetched, ordered by `order`, limited to the first `READING_LIST_DETAIL_PAGINATE_BY` (50) — additional items are fetched via `ReadingListItemsLoadMore`
- `reading_list_items_count`: Total count of items in the list (via `len()` on the prefetched queryset, not a separate `COUNT` query)
- `is_owner`: Boolean from `can_manage_reading_list()`
- `can_assign_to_metron`: True when the list is not already Metron-owned and `can_assign_reading_list_to_metron()` passes
- `user_rating`: User's own rating, pulled from the prefetched `user_rating_list` (if authenticated and has rated)
- `average_rating` / `rating_count`: From the annotated queryset
- `start_year` / `end_year`: From the annotated queryset
- `issue_type_breakdown`: Per-`issue_type` counts (Prologue/Core/Tie-In/Epilogue) with a display label and bar color, computed in Python from the already-prefetched items
- `series_breakdown` / `publisher_breakdown`: Per-series and per-publisher issue counts, also computed from the prefetched items (no extra queries)
- `featured_creators`: Top 6 creators by issue count across the list's issues (writer/artist roles only), with a `roles` string ("Writer", "Artist", or both)
- `top_characters`: Top 12 characters by appearance count across the list's issues

**Query Optimizations:**

The detail view is heavily optimized to reduce database queries:

1. **Prefetch reading list items** with related issue, series, series_type, and publisher data
2. **Annotate year ranges and rating aggregates** instead of using expensive properties or separate queries
3. **Prefetch ratings** (all ratings, plus the current user's own rating via a second `Prefetch` with `to_attr="user_rating_list"`) to avoid N+1 queries
4. **Compute breakdowns/top creators/top characters from the already-prefetched `reading_list_items`** in Python where possible, and with small aggregate queries (`Creator`/`Character` annotated + sliced) otherwise — avoids re-querying `Publisher` separately
5. Breakdown/creator/character computation only runs when `reading_list_items_count > 0`

**URL:** `/reading-lists/<slug>/`

### Authenticated Views

#### UserReadingListListView

```python
class UserReadingListListView(LoginRequiredMixin, ListView):
    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    context_object_name = "reading_lists"
    paginate_by = 30

    def get_queryset(self):
        return ReadingList.objects.filter(user=self.request.user).annotate(...)
```

Same `issue_count`/`average_rating`/`rating_count`/`start_year_annotated`/`end_year_annotated` annotations as `ReadingListListView`, scoped to `user=self.request.user` (no visibility filtering needed — it's always the current user's own lists). Sets `is_user_view = True` in context so the template can adjust its empty-state messaging.

**URL:** `/reading-lists/my-lists/`

#### ReadingListCreateView

```python
class ReadingListCreateView(LoginRequiredMixin, CreateView):
    model = ReadingList
    form_class = ReadingListForm
```

**Form Customization:**

- Non-admin users: Attribution fields removed from form
- Auto-sets `user` to current user in `form_valid()`

**URL:** `/reading-lists/create/`

#### ReadingListUpdateView

```python
class ReadingListUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ReadingList
    form_class = ReadingListForm

    def test_func(self):
        return can_manage_reading_list(self.request.user, self.get_object())
```

**Form Customization:**

- Non-admin users: Attribution fields removed from form (same `get_form()` override as `ReadingListCreateView`)

**URL:** `/reading-lists/<slug>/update/`

#### ReadingListDeleteView

```python
class ReadingListDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ReadingList
    template_name = "reading_lists/readinglist_confirm_delete.html"
    success_url = reverse_lazy("reading-list:my-lists")

    def test_func(self):
        return can_manage_reading_list(self.request.user, self.get_object())
```

**URL:** `/reading-lists/<slug>/delete/`

#### AssignReadingListToMetronView

```python
class AssignReadingListToMetronView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return can_assign_reading_list_to_metron(self.request.user)
```

**Purpose:** Reassigns a reading list's `user` foreign key to the "Metron" account, allowing curators to adopt community-submitted lists as official reading orders.

**Permission Check:**

Uses `can_assign_reading_list_to_metron()` (see [Permission Helpers](#views-and-urls)), independent of `can_manage_reading_list()`/ownership — a user does **not** need to own or already be able to manage the list.

**Behavior:**

1. `GET`: Renders a confirmation page (`readinglist_confirm_assign_metron.html`). If the list is already owned by Metron, redirects straight to the detail page instead.
2. `POST`: Looks up the `CustomUser` with `username="Metron"`.
    - If it doesn't exist, shows an error message and redirects (no exception raised).
    - Otherwise reassigns `reading_list.user` to the Metron account, saves, and shows a success message.
    - A no-op (but still a redirect) if the list is already Metron-owned.

**URL:** `/reading-lists/<slug>/assign-to-metron/`

#### AddIssueWithAutocompleteView

```python
class AddIssueWithAutocompleteView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AddIssueWithSearchForm
    template_name = "reading_lists/add_issue_autocomplete.html"
```

**Complex Logic:**

1. Parses `issue_order` (comma-separated issue IDs)
2. Distinguishes existing vs. new issues
3. Updates order for existing issues
4. Creates ReadingListItem for new issues
5. Provides detailed feedback (added, reordered, skipped)

**URL:** `/reading-lists/<slug>/add-issue/`

#### AddIssuesFromSeriesView

```python
class AddIssuesFromSeriesView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AddIssuesFromSeriesForm
    template_name = "reading_lists/add_issues_from_series.html"
```

**Purpose:** Bulk addition of issues from a series to a reading list.

**Complex Logic:**

1. Fetches all issues from selected series ordered by cover date
2. Applies optional range filtering (start/end issue numbers)
3. Filters out duplicate issues
4. Positions new issues at beginning or end
5. Uses `bulk_create()` for efficient database operations
6. Handles reordering when inserting at beginning

**Range Filtering:**

- **All issues**: Adds entire series
- **Start + End**: Adds issues between specified numbers
- **Start only**: Adds from start number to series end
- **End only**: Adds from series beginning to end number

**Performance Optimizations:**

- Uses `bulk_create()` for batch insertion
- Filters queryset before iteration
- Single aggregate query for max order

**URL:** `/reading-lists/<slug>/add-from-series/`

#### AddIssuesFromArcView

```python
class AddIssuesFromArcView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    form_class = AddIssuesFromArcForm
    template_name = "reading_lists/add_issues_from_arc.html"
```

**Purpose:** Bulk addition of all issues from a story arc to a reading list.

**Complex Logic:**

1. Fetches all issues from selected arc ordered by cover date
2. Filters out duplicate issues
3. Positions new issues at beginning or end
4. Uses `bulk_create()` for efficient database operations
5. Handles reordering when inserting at beginning

**Performance Optimizations:**

- Uses `bulk_create()` for batch insertion
- Single aggregate query for max order
- Prefetches issue relationships

**URL:** `/reading-lists/<slug>/add-from-arc/`

#### RemoveIssueFromReadingListView

```python
class RemoveIssueFromReadingListView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ReadingListItem
    template_name = "reading_lists/remove_issue_confirm.html"
```

**URL:** `/reading-lists/<slug>/remove-issue/<item_pk>/`

#### ReadingListItemsLoadMore

```python
class ReadingListItemsLoadMore(LazyLoadMixin, View):
    model = ReadingList
    relation_name = "reading_list_items"
    template_name = "reading_lists/partials/readinglist_item_list.html"
    context_object_name = "reading_list_items"
    slug_context_name = "reading_list_slug"
```

**Purpose:** HTMX "Load More" endpoint for reading list items beyond the first `READING_LIST_DETAIL_PAGINATE_BY` (50) shown on initial page load. Built on the shared `LazyLoadMixin` (`comicsdb/views/mixins.py`), which is also used by other detail pages (e.g. Universe, Team) for the same load-more pattern.

**Behavior:**

- Overrides `get()` to re-apply the same public/own/Metron visibility filtering as `ReadingListDetailView` before fetching the parent `ReadingList` by slug (`LazyLoadMixin`'s default `get()` doesn't filter by permission, since most consumers don't need it)
- Paginates by `DETAIL_PAGINATE_BY` (30, from `comicsdb/views/constants.py` — **not** the 50 used for the initial detail-page load)
- Adds `is_owner` (via `can_manage_reading_list()`) to context so the rendered items include working remove/edit-type buttons
- Renders `partials/readinglist_item_list.html`, which also re-renders the "Load More" button (or omits it once `has_more` is `False`) via an out-of-band (`hx-swap-oob`) swap

**URL:** `/reading-lists/<slug>/items-load-more/`

#### update_reading_list_rating (Function-Based View)

```python
@login_required
@require_POST
def update_reading_list_rating(request, slug):
    """HTMX view to update the rating of a reading list."""
```

**Purpose:** HTMX-powered endpoint for updating reading list ratings.

**Validation Rules:**

1. Must be authenticated (`@login_required`)
2. Must use POST method (`@require_POST`)
3. Can only rate public lists (returns 403 for private lists)
4. Cannot rate own lists (returns 403 for owner)
5. Rating value must be 1-5 or 0 (to clear rating)

**HTMX Integration:**

- Accepts POST requests with `rating` parameter
- Returns rendered partial template with updated rating data
- Uses `outerHTML` swap to update the rating component
- Provides instant feedback without page reload

**Rating Logic:**

```python
rating_value = request.POST.get("rating")
if MIN_RATING <= rating <= MAX_RATING:
    # Update or create rating
    ReadingListRating.objects.update_or_create(
        reading_list=reading_list,
        user=request.user,
        defaults={"rating": rating},
    )
elif rating == 0:
    # Clear rating
    ReadingListRating.objects.filter(
        reading_list=reading_list,
        user=request.user,
    ).delete()
```

**Response:**

Returns the `reading_list_rating.html` partial template with context:

- `reading_list`: The rated reading list
- `user_rating`: User's updated rating object
- `average_rating`: Recalculated average rating
- `rating_count`: Updated rating count

**URL:** `/reading-lists/<slug>/rate/`

#### edit_issue_type (Function-Based View)

```python
@login_required
def edit_issue_type(request, slug, item_pk):
    """HTMX view to show the edit form for issue type."""
```

**Purpose:** HTMX-powered endpoint for displaying the issue type edit form.

**Validation Rules:**

1. Must be authenticated (`@login_required`)
2. Must have permission to manage the reading list
3. Reading list item must exist

**HTMX Integration:**

- Accepts GET requests
- Returns rendered partial template with edit form
- Uses `outerHTML` swap to replace display with edit mode
- Provides instant inline editing without page navigation

**URL:** `/reading-lists/<slug>/item/<item_pk>/edit-type/`

#### update_issue_type (Function-Based View)

```python
@login_required
@require_POST
def update_issue_type(request, slug, item_pk):
    """HTMX view to update the issue type of a reading list item."""
```

**Purpose:** HTMX-powered endpoint for saving issue type changes.

**Validation Rules:**

1. Must be authenticated (`@login_required`)
2. Must use POST method (`@require_POST`)
3. Must have permission to manage the reading list
4. Issue type value must be valid or empty

**Issue Type Validation:**

```python
issue_type = request.POST.get("issue_type", "")
if issue_type in dict(ReadingListItem.IssueType.choices) or issue_type == "":
    item.issue_type = issue_type
    item.save()
```

**HTMX Integration:**

- Accepts POST requests with `issue_type` parameter
- Returns rendered partial template with updated display
- Uses `outerHTML` swap to replace edit form with display
- Provides instant feedback without page reload

**Supported Values:**

- `PROLOGUE`, `CORE`, `TIE_IN`, `EPILOGUE`: Valid issue types
- Empty string `""`: Clears the issue type
- Invalid values: Ignored, no change made

**URL:** `/reading-lists/<slug>/item/<item_pk>/update-type/`

#### cancel_edit_issue_type (Function-Based View)

```python
@login_required
def cancel_edit_issue_type(request, slug, item_pk):
    """HTMX view to cancel editing and return to display mode."""
```

**Purpose:** HTMX-powered endpoint for canceling issue type editing.

**Validation Rules:**

1. Must be authenticated (`@login_required`)
2. Must have permission to manage the reading list

**HTMX Integration:**

- Accepts GET requests
- Returns rendered partial template with original display
- Uses `outerHTML` swap to replace edit form with display
- Discards any unsaved changes

**URL:** `/reading-lists/<slug>/item/<item_pk>/cancel-edit-type/`

### URL Configuration

**File:** `reading_lists/urls.py`

```python
app_name = "reading-list"
urlpatterns = [
    path("", ReadingListListView.as_view(), name="list"),
    re_path(r"^search/?$", SearchReadingListListView.as_view(), name="search"),
    path("my-lists/", UserReadingListListView.as_view(), name="my-lists"),
    path("create/", ReadingListCreateView.as_view(), name="create"),
    path("<slug:slug>/", ReadingListDetailView.as_view(), name="detail"),
    path("<slug:slug>/update/", ReadingListUpdateView.as_view(), name="update"),
    path("<slug:slug>/delete/", ReadingListDeleteView.as_view(), name="delete"),
    path("<slug:slug>/assign-to-metron/", AssignReadingListToMetronView.as_view(), name="assign-to-metron"),
    path("<slug:slug>/add-issue/", AddIssueWithAutocompleteView.as_view(), name="add-issue"),
    path("<slug:slug>/add-from-series/", AddIssuesFromSeriesView.as_view(), name="add-from-series"),
    path("<slug:slug>/add-from-arc/", AddIssuesFromArcView.as_view(), name="add-from-arc"),
    path("<slug:slug>/remove-issue/<int:item_pk>/", RemoveIssueFromReadingListView.as_view(), name="remove-issue"),
    path("<slug:slug>/items-load-more/", ReadingListItemsLoadMore.as_view(), name="items-load-more"),
    path("<slug:slug>/rate/", update_reading_list_rating, name="rate"),
    path("<slug:slug>/item/<int:item_pk>/edit-type/", edit_issue_type, name="edit-issue-type"),
    path("<slug:slug>/item/<int:item_pk>/update-type/", update_issue_type, name="update-issue-type"),
    path("<slug:slug>/item/<int:item_pk>/cancel-edit-type/", cancel_edit_issue_type, name="cancel-edit-issue-type"),
]
```

## Forms

**File:** `reading_lists/forms.py`

### ReadingListForm

```python
class ReadingListForm(forms.ModelForm):
    class Meta:
        model = ReadingList
        fields = (
            "name",
            "desc",
            "image",
            "is_private",
            "list_type",
            "attribution_source",
            "attribution_url",
        )
```

`image` uses `forms.ClearableFileInput()` so an existing cover can be removed; `list_type` and `attribution_source` render as `Select` dropdowns. Custom labels and help text are set for `desc`, `is_private`, `list_type`, `attribution_source`, and `attribution_url` in `Meta`.

**Dynamic Field Removal:**
Attribution fields (`attribution_source`, `attribution_url`) are removed in the view's `get_form()` for non-admin (non-`is_staff`) users — `list_type` and `image` remain available to all users.

### AddIssueWithSearchForm

```python
class AddIssueWithSearchForm(forms.Form):
    issues = forms.ModelMultipleChoiceField(
        queryset=Issue.objects.select_related("series", "series__series_type").all(),
        widget=widgets.AutocompleteWidget(
            ac_class=IssueAutocomplete,
            options={"multiselect": True},
        ),
    )
    issue_order = forms.CharField(widget=forms.HiddenInput())
```

**Hidden Field:**
`issue_order` stores comma-separated issue IDs after drag-and-drop reordering.

### AddIssuesFromSeriesForm

```python
class AddIssuesFromSeriesForm(forms.Form):
    series = forms.ModelChoiceField(
        queryset=Series.objects.select_related("series_type").all(),
        widget=widgets.AutocompleteWidget(ac_class=SeriesAutocomplete),
    )
    range_type = forms.ChoiceField(
        choices=[("all", "All issues"), ("range", "Issue range")],
        widget=forms.RadioSelect(),
    )
    start_number = forms.CharField(max_length=25, required=False)
    end_number = forms.CharField(max_length=25, required=False)
    position = forms.ChoiceField(
        choices=[("end", "At the end"), ("beginning", "At the beginning")],
        widget=forms.RadioSelect(),
    )
```

**Features:**

- **Series autocomplete**: Uses `SeriesAutocomplete` for efficient search
- **Radio buttons**: HTMX-based UI for range type selection
- **Flexible range**: Optional start/end numbers
- **Position control**: Add at beginning or end of list

**Form Validation:**

```python
def clean(self):
    if range_type == "range" and not start_number and not end_number:
        raise forms.ValidationError(
            "Please specify at least a start or end issue number for the range."
        )
```

**Use Case:**
Designed for bulk operations where users need to add 10-1000+ issues from a single series efficiently.

### AddIssuesFromArcForm

```python
class AddIssuesFromArcForm(forms.Form):
    arc = forms.ModelChoiceField(
        queryset=Arc.objects.all(),
        widget=widgets.AutocompleteWidget(ac_class=ArcAutocomplete),
    )
    position = forms.ChoiceField(
        choices=[("end", "At the end"), ("beginning", "At the beginning")],
        widget=forms.RadioSelect(),
    )
```

**Features:**

- **Arc autocomplete**: Uses `ArcAutocomplete` for efficient search
- **Radio buttons**: Simple UI for position selection
- **Position control**: Add at beginning or end of list

**Use Case:**
Designed for adding complete story arcs that span multiple series (crossover events, major storylines).

## Permissions

### Permission Strategy

The app uses `UserPassesTestMixin` for permission checks rather than object-level permissions. Rather than each view duplicating the ownership/group logic in its own `test_func()`, two shared functions in `reading_lists/views.py` are reused everywhere (see [Permission Helpers](#views-and-urls)):

```python
def can_manage_reading_list(user, reading_list):
    is_owner = reading_list.user == user
    if reading_list.user.username == "Metron":
        is_staff = user.is_staff
        is_editor_group = user.groups.filter(name="reading list editor").exists()
        return is_owner or is_staff or is_editor_group
    return is_owner


def can_assign_reading_list_to_metron(user):
    return user.is_staff or user.groups.filter(name="reading list editor").exists()
```

`can_manage_reading_list()` backs `test_func()` on `ReadingListUpdateView`, `ReadingListDeleteView`, `RemoveIssueFromReadingListView`, `AddIssueWithAutocompleteView`, `AddIssuesFromSeriesView`, and `AddIssuesFromArcView`, and is also called directly (not via a mixin) inside `edit_issue_type`, `update_issue_type`, and `cancel_edit_issue_type` since those are function-based views.

**"reading list editor" Group:**

A Django group (note: **lowercase** name, matched exactly via `groups.filter(name="reading list editor")`) created via migration that provides special permissions for managing Metron user's reading lists.

**Migration:** `0002_create_reading_list_editor_group.py`

**Purpose:**

- Allows designated curators to manage official reading orders
- Provides elevated permissions without full admin access
- Separates content curation from system administration

### Assign-to-Metron Permission

`AssignReadingListToMetronView` (used to reassign a list's ownership to the "Metron" account) uses `can_assign_reading_list_to_metron()` rather than `can_manage_reading_list()`, since it must apply to lists the user does **not** already own or manage.

This is intentionally broader in scope (any reading list) but narrower in who qualifies (staff or "reading list editor" group members only — plain ownership does not grant this permission).

### Permission Levels

**Unauthenticated Users:**

- Can view public reading lists
- Cannot create, edit, or delete lists
- Cannot view private lists

**Authenticated Users:**

- All unauthenticated permissions
- Can create reading lists
- Can edit/delete own lists
- Can view own private lists
- Cannot edit others' lists

**"reading list editor" Group:**

- All authenticated permissions
- Can edit/delete Metron user's lists
- Can view Metron's private lists
- Can reassign any reading list (including other users' lists) to the Metron account
- Cannot set attribution fields (admin-only)

**Admin Users (is_staff=True):**

- All authenticated permissions
- Can edit/delete Metron user's lists
- Can view Metron's private lists
- Can reassign any reading list (including other users' lists) to the Metron account
- Can set attribution fields

### Visibility Rules

Implemented as near-identical queryset filtering repeated across `ReadingListListView`, `SearchReadingListListView`, `ReadingListDetailView`, the API's `ReadingListViewSet`, and `ReadingListItemsLoadMore` (each needs it inline since it's blended with different annotations/prefetches, so there's no single shared helper):

```python
def get_queryset(self):
    queryset = ReadingList.objects.all()

    if not self.request.user.is_authenticated:
        return queryset.filter(is_private=False)

    is_editor = self.request.user.groups.filter(name="reading list editor").exists()
    if self.request.user.is_staff or is_editor:
        try:
            metron_user = CustomUser.objects.get(username="Metron")
            return queryset.filter(
                Q(is_private=False) |
                Q(user=self.request.user) |
                Q(user=metron_user)
            ).distinct()
        except CustomUser.DoesNotExist:
            pass

    return queryset.filter(
        Q(is_private=False) | Q(user=self.request.user)
    ).distinct()
```

Note the web views (list/detail/lazy-load) include the "reading list editor" group in the Metron-visibility branch alongside `is_staff`; the API's `ReadingListViewSet.get_queryset()` currently only checks `is_staff` for that branch (editor-group members still see their own + public lists via the API, just not Metron's private ones).

## Autocomplete

**File:** `comicsdb/autocomplete.py`

### IssueAutocomplete

```python
class IssueAutocomplete(ModelAutocomplete):
    model = Issue
    search_attrs = ["series__name", "number"]
```

**Smart Search Implementation:**

```python
def get_query_filtered_queryset(cls, search, context):
    base_qs = cls.get_queryset()

    if "#" in search:
        parts = search.split("#", 1)
        series_part = parts[0].strip()
        number_part = parts[1].strip()

        conditions = []
        if series_part:
            conditions.append(Q(series__name__icontains=series_part))
        if number_part:
            conditions.append(Q(number__icontains=number_part))

        return base_qs.filter(reduce(operator.and_, conditions))
    else:
        conditions = [Q(**{f"{attr}__icontains": search}) for attr in cls.search_attrs]
        return base_qs.filter(reduce(operator.or_, conditions))
```

**Features:**

- Basic search: OR across series name and number
- Smart search: AND between series and number when `#` present
- Optimized queryset with `select_related("series", "series__series_type")`

### SeriesAutocomplete

```python
class SeriesAutocomplete(ModelAutocomplete):
    model = Series
    search_attrs = ["name"]
```

**Usage:**
Used in `AddIssuesFromSeriesForm` for bulk addition feature.

**Queryset:**

```python
queryset = Series.objects.select_related("series_type").all()
```

**Features:**

- Simple name-based search
- Optimized with `select_related()` for series type
- Returns formatted results with series type information

### ArcAutocomplete

```python
class ArcAutocomplete(ModelAutocomplete):
    model = Arc
    search_attrs = ["name"]
```

**Usage:**
Used in `AddIssuesFromArcForm` for arc-based bulk addition feature.

**Features:**

- Simple name-based search
- Returns formatted results with arc names
- Enables quick selection of story arcs

## Filters

**File:** `comicsdb/filters/reading_list.py`

Both filters share a `filter_reading_lists_by_publisher()` helper, defined at module level rather than duplicated as a method:

```python
def filter_reading_lists_by_publisher(queryset, value):
    matching_ids = (
        ReadingList.objects.filter(
            reading_list_items__issue__series__publisher__name__icontains=value
        )
        .values("id")
        .distinct()
    )
    return queryset.filter(id__in=matching_ids)
```

It runs as a subquery (`id__in=...`) specifically to avoid combining the `reading_list_items__issue__series__publisher` JOIN chain with the `COUNT`/`AVG` rating and issue-count aggregations on the outer queryset, which was measured to cause extreme slowness.

### ReadingListFilter (API Filter)

Django filter for API endpoints (`django_filters.rest_framework`).

```python
class ReadingListFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="unaccent__icontains")
    user = filters.NumberFilter(field_name="user__id", lookup_expr="exact")
    username = filters.CharFilter(field_name="user__username", lookup_expr="icontains")
    attribution_source = filters.ChoiceFilter(choices=ReadingList.AttributionSource.choices)
    list_type = filters.ChoiceFilter(choices=ReadingList.ListType.choices)
    is_private = filters.BooleanFilter()
    modified_gt = filters.DateTimeFilter(field_name="modified", lookup_expr="gt")
    average_rating__gte = filters.NumberFilter(
        field_name="average_rating", lookup_expr="gte", label="Minimum Rating",
    )
    publisher = filters.CharFilter(label="Publisher", method="filter_by_publisher")
```

**Fields:**

- `name`: Accent-insensitive, case-insensitive search on list name (`unaccent__icontains`)
- `user`: Filter by exact user ID
- `username`: Case-insensitive search on username
- `attribution_source`: Exact match against `AttributionSource` choices
- `list_type`: Exact match against `ListType` choices
- `is_private`: Filter by privacy status
- `modified_gt`: Filter by modification date (greater than) — used by clients to sync recently-changed lists
- `average_rating__gte`: Filter by minimum average rating (1-5)
- `publisher`: Free-text publisher name match via `filter_reading_lists_by_publisher()`

### ReadingListViewFilter (Web View Filter)

Django filter for web views (plain `django_filters`, not the REST variant), with a dedicated quick-search filter.

```python
class QuickSearchFilter(df.CharFilter):
    """Quick search by reading list name."""

    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(operator.and_, (Q(name__unaccent__icontains=q) for q in query_list))
            )
        return super().filter(qs, value)


class ReadingListViewFilter(df.FilterSet):
    q = QuickSearchFilter(label="Quick Search")
    name = df.CharFilter(label="List Name", lookup_expr="unaccent__icontains")
    username = df.CharFilter(label="Creator", field_name="user__username", lookup_expr="icontains")
    attribution_source = df.ChoiceFilter(
        label="Attribution Source", choices=ReadingList.AttributionSource.choices
    )
    list_type = df.ChoiceFilter(label="List Type", choices=ReadingList.ListType.choices)
    is_private = df.BooleanFilter(label="Private")
    publisher = df.CharFilter(label="Publisher", method="filter_by_publisher")
    average_rating__gte = df.NumberFilter(
        field_name="average_rating", lookup_expr="gte", label="Minimum Rating",
    )
```

**Features:**

- `q` (`QuickSearchFilter`): Splits the query on whitespace and AND-matches every term against `name` (unaccent-aware) — distinct from `SearchReadingListListView`'s `SearchMixin`-based search, which also matches `username`/`attribution_source` and is used only on the dedicated `/search/` URL
- Individual field filters (`name`, `username`, `attribution_source`, `list_type`, `publisher`, `is_private`, `average_rating__gte`) power the collapsible "Advanced Filters" panel
- Integrated with `ReadingListListView` (applied via `filtered.qs` in `get_queryset()`) — **not** used by `SearchReadingListListView`, which applies `q` through `SearchMixin` instead
- Removable filter chips are built separately in `build_active_filters()` (`reading_lists/views.py`), not by this FilterSet

**Rating Filter Options:**

The web interface provides a dropdown with:

- All Ratings (no filter)
- 1+ Stars
- 2+ Stars
- 3+ Stars
- 4+ Stars
- 5 Stars

**Filter Template:** `partials/readinglist_filter.html` — includes the quick-search field plus a `<details>`-collapsed "Advanced Filters" panel (name, creator, publisher, list type, attribution source, minimum rating, and — for authenticated users only — a privacy filter).

## Templates

**Directory:** `reading_lists/templates/reading_lists/`

### Template Files

| Template | Purpose | Key Features |
| ---------- | --------- | -------------- |
| `readinglist_list.html` | List all public lists and user's own lists | Grid of `readinglist_card.html` cards, filter panel, pagination, context-sensitive nav |
| `readinglist_detail.html` | Single list detail | Ordered issues (lazy-loaded past the first 50), add/remove controls, bulk add buttons, stats (breakdowns, featured creators, top characters) |
| `readinglist_form.html` | Create/edit form | Dynamic field visibility, cover image upload |
| `readinglist_confirm_delete.html` | Delete confirmation | Issue count warning |
| `readinglist_confirm_assign_metron.html` | Assign-to-Metron confirmation | Staff/editor-only, warns ownership change is not undoable from the UI |
| `add_issue_autocomplete.html` | Add issues interface | Autocomplete, drag-drop, preview |
| `add_issues_from_series.html` | Bulk add from series | Series autocomplete, HTMX range toggle, usage tips |
| `add_issues_from_arc.html` | Bulk add from arc | Arc autocomplete, position selection, usage tips |
| `remove_issue_confirm.html` | Remove issue confirmation | Issue details |
| `partials/readinglist_card.html` | List card (grid item) | Cover thumbnail, list type tag, year range, rating stars, privacy badge, truncated description |
| `partials/readinglist_filter.html` | Filter/search panel | Quick search + collapsible advanced filters, active-filter tag |
| `partials/reading_list_rating.html` | Rating component | HTMX-powered star rating, average display |
| `partials/readinglist_item.html` | Single item display | Issue type badge, inline edit button, remove button |
| `partials/readinglist_item_edit.html` | Single item edit form | Issue type dropdown, save/cancel buttons |
| `partials/readinglist_item_list.html` | Item list + load-more button | Rendered by `ReadingListItemsLoadMore`; re-renders itself and the load-more button via an out-of-band (`hx-swap-oob`) swap |

### Template Context

**Common Context Variables:**

- `reading_list`: ReadingList instance
- `reading_list_items`: Ordered queryset of ReadingListItem
- `is_owner`: Boolean for edit permissions
- `can_assign_to_metron`: Boolean; True when the current user is staff or a "reading list editor" group member and the list is not already Metron-owned. Controls visibility of the "Assign to Metron" button, independently of `is_owner`
- `user`: Current user (from request)

### HTMX Integration

**File:** `add_issues_from_series.html`

The series bulk addition template uses HTMX for client-side interactivity:

```html
<div class="control"
     hx-on:change="
         if (event.target.name === 'range_type') {
             const rangeFields = document.getElementById('range-fields');
             rangeFields.style.display = event.target.value === 'range' ? 'block' : 'none';
         }
     ">
```

**Benefits:**

- Co-located event handling with UI elements
- ~50% reduction in JavaScript code
- Consistent with project's HTMX-first approach
- Maintains progressive enhancement

**Initialization:**

```javascript
htmx.onLoad(function() {
    const selectedRadio = document.querySelector('input[name="range_type"]:checked');
    if (selectedRadio && selectedRadio.value === 'range') {
        document.getElementById('range-fields').style.display = 'block';
    }
});
```

### Rating Partial Template

**File:** `partials/reading_list_rating.html`

The rating system uses HTMX for instant, no-reload rating updates:

```html
<button type="button"
        class="star-button"
        hx-post="{% url 'reading-list:rate' reading_list.slug %}"
        hx-vals='{"rating": "{{ forloop.counter }}"}'
        hx-target="#reading-list-rating-{{ reading_list.pk }}"
        hx-swap="outerHTML">
    <i class="fas fa-star"></i>
</button>
```

**Features:**

- **HTMX POST Requests**: Star clicks trigger POST to rating endpoint
- **Partial Replacement**: Uses `outerHTML` swap to update entire rating component
- **CSRF Protection**: CSRF token configured globally in detail view JavaScript
- **Inline Styles**: Component includes scoped CSS to avoid style conflicts
- **Accessibility**: Proper labels and ARIA attributes for screen readers

**Rating Display:**

1. **Average Rating**: Displays filled/unfilled stars based on average (always visible for public lists)
2. **User Rating**: Interactive stars for authenticated non-owners
3. **Clear Button**: × button to remove user's rating

**CSRF Configuration:**

```javascript
document.body.addEventListener('htmx:configRequest', (event) => {
    event.detail.headers['X-CSRFToken'] = '{{ csrf_token }}';
});
```

This ensures all HTMX requests include the CSRF token for security.

### Issue Type Editing Partials

**Files:**

- `partials/readinglist_item.html` - Display mode
- `partials/readinglist_item_edit.html` - Edit mode

The issue type editing system uses HTMX for inline, no-reload editing:

**Display Mode Template (`readinglist_item.html`):**

```html
<li id="item-{{ item.pk }}">
    <div class="level">
        <div class="level-left">
            <div class="level-item">
                <div>
                    <a href="{% url 'issue:detail' item.issue.slug %}">{{ item.issue }}</a>
                    <span class="has-text-grey-light">— {{ item.issue.cover_date|date:"M Y" }}</span>
                    {% if item.issue_type %}
                        <span class="tag is-info is-light ml-2">{{ item.get_issue_type_display }}</span>
                    {% endif %}
                </div>
            </div>
        </div>
        {% if is_owner %}
            <div class="level-right">
                <div class="level-item">
                    <div class="buttons has-addons">
                        <button class="button is-small is-info is-outlined"
                                hx-get="{% url 'reading-list:edit-issue-type' reading_list_slug item.pk %}"
                                hx-target="#item-{{ item.pk }}"
                                hx-swap="outerHTML"
                                title="Edit issue type">
                            <span class="icon is-small">
                                <i class="fas fa-tag"></i>
                            </span>
                        </button>
                        <a href="{% url 'reading-list:remove-issue' reading_list_slug item.pk %}"
                           class="button is-small is-danger is-outlined"
                           title="Remove from list">
                            <span class="icon is-small">
                                <i class="fas fa-times"></i>
                            </span>
                        </a>
                    </div>
                </div>
            </div>
        {% endif %}
    </div>
</li>
```

**Features:**

- **Issue Type Badge**: Displays colored badge when issue has a type
- **Edit Button**: Tag icon button triggers edit mode via HTMX GET
- **Target Swap**: Uses `outerHTML` to replace entire list item with edit form
- **Permission-Based**: Edit button only shown to owners/editors

**Edit Mode Template (`readinglist_item_edit.html`):**

```html
<li id="item-{{ item.pk }}">
    <div class="level">
        <div class="level-left">
            <div class="level-item">
                <div>
                    <a href="{% url 'issue:detail' item.issue.slug %}">{{ item.issue }}</a>
                    <span class="has-text-grey-light">— {{ item.issue.cover_date|date:"M Y" }}</span>
                </div>
            </div>
            <div class="level-item">
                <form hx-post="{% url 'reading-list:update-issue-type' reading_list_slug item.pk %}"
                      hx-target="#item-{{ item.pk }}"
                      hx-swap="outerHTML">
                    {% csrf_token %}
                    <div class="field has-addons">
                        <div class="control">
                            <div class="select is-small">
                                <select name="issue_type">
                                    <option value="">-- No Type --</option>
                                    <option value="PROLOGUE" {% if item.issue_type == 'PROLOGUE' %}selected{% endif %}>Prologue</option>
                                    <option value="CORE" {% if item.issue_type == 'CORE' %}selected{% endif %}>Core Issue</option>
                                    <option value="TIE_IN" {% if item.issue_type == 'TIE_IN' %}selected{% endif %}>Tie-In</option>
                                    <option value="EPILOGUE" {% if item.issue_type == 'EPILOGUE' %}selected{% endif %}>Epilogue</option>
                                </select>
                            </div>
                        </div>
                        <div class="control">
                            <button type="submit" class="button is-small is-success">
                                <span class="icon is-small">
                                    <i class="fas fa-check"></i>
                                </span>
                            </button>
                        </div>
                        <div class="control">
                            <button type="button"
                                    class="button is-small"
                                    hx-get="{% url 'reading-list:cancel-edit-issue-type' reading_list_slug item.pk %}"
                                    hx-target="#item-{{ item.pk }}"
                                    hx-swap="outerHTML">
                                <span class="icon is-small">
                                    <i class="fas fa-times"></i>
                                </span>
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    </div>
</li>
```

**Features:**

- **Dropdown Selection**: All four issue types plus "No Type" option
- **Current Value**: Pre-selects current issue type
- **Save Button**: Checkmark icon submits via HTMX POST
- **Cancel Button**: X icon reverts to display mode via HTMX GET
- **Inline Form**: Form embedded directly in the list item
- **CSRF Protection**: Token included in form

**HTMX Workflow:**

1. User clicks edit button (tag icon)
2. HTMX GET request to `edit-issue-type` endpoint
3. Server returns edit form template
4. Form replaces list item via `outerHTML` swap
5. User selects type and clicks save OR clicks cancel
6. HTMX POST/GET request to `update-issue-type` or `cancel-edit-issue-type`
7. Server returns display template with updated/original data
8. Display replaces form via `outerHTML` swap

**Benefits:**

- No page reload required
- Instant visual feedback
- Progressive enhancement (works without JavaScript)
- Consistent with project's HTMX patterns
- Minimal JavaScript code required

## Database Optimization

### QuerySet Optimizations

**List Views:**

```python
queryset = ReadingList.objects.select_related("user").annotate(
    issue_count=Count("issues", distinct=True),
    average_rating=Avg("ratings__rating"),
    rating_count=Count("ratings", distinct=True),
    start_year_annotated=Min("reading_list_items__issue__cover_date__year"),
    end_year_annotated=Max("reading_list_items__issue__cover_date__year"),
)
```

`issue_count` uses `distinct=True` because it's computed alongside the `ratings` join — without it, the `Count` would be inflated by the cross-join between `reading_list_items`/`issues` and `ratings`.

**Detail View:**

```python
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

# For authenticated users, prefetch their own rating
if request.user.is_authenticated:
    queryset = queryset.prefetch_related(
        Prefetch(
            "ratings",
            queryset=ReadingListRating.objects.filter(user=request.user),
            to_attr="user_rating_list",
        )
    )
```

**Benefits:**

- `select_related()`: Reduces queries for ForeignKey relationships
- `prefetch_related()`: Optimizes M2M and reverse ForeignKey queries
- `annotate()`: Computes counts, averages, and aggregates in database
- `Prefetch()`: Fine-grained control over prefetch querysets
- **Rating Optimizations**: All rating data fetched in initial query
- **Year Range Annotations**: Replaces the `start_year`/`end_year` model properties with database aggregation for list/detail views (the properties still exist on the model and run their own queries if accessed directly, e.g. from a shell or the import command)
- **Breakdown/Stats Extraction**: `issue_type_breakdown`, `series_breakdown`, and `publisher_breakdown` are all computed in Python from the already-prefetched `reading_list_items` in `ReadingListDetailView.get_context_data()` — avoids a separate query per breakdown and avoids the `publishers` property's own `Publisher.objects.filter(...).distinct()` query

### Indexes

**ReadingListItem:**

```python
class Meta:
    indexes = [
        models.Index(fields=["reading_list", "order"], name="reading_list_order_idx"),
    ]
```

**ReadingListRating:**

```python
class Meta:
    indexes = [
        models.Index(fields=["reading_list", "user"]),
    ]
```

**Composite Indexes:**

- `ReadingListItem`: `(reading_list, order)` - optimizes ordering queries
- `ReadingListRating`: `(reading_list, user)` - optimizes rating lookups and aggregations

**Standard Indexes:**

- ForeignKey fields auto-indexed
- Unique constraints create indexes
- Slug field indexed via CommonInfo

### Database Constraints

**Unique Constraints:**

- `ReadingList`: `(user, name, attribution_source)` - prevents duplicate list names per user within the same attribution source
- `ReadingListItem`: `(reading_list, issue)` - prevents duplicate issues in a list
- `ReadingListRating`: `(reading_list, user)` - one rating per user per list

**Benefits:**

- Prevents duplicate data at database level
- Faster lookups on constrained fields
- Data integrity enforcement
- Enables `update_or_create()` for idempotent rating updates

## Dependencies

### Internal Dependencies

**comicsdb.models.Issue:**

```python
from comicsdb.models.issue import Issue
```

Used for issue data and M2M relationship.

**comicsdb.models.Publisher:**

```python
from comicsdb.models.publisher import Publisher
```

Used in the `ReadingList.publishers` model property (a separate query, not used by the detail view's `publisher_breakdown`, which is computed from prefetched data instead).

**comicsdb.models.character.Character, comicsdb.models.creator.Creator, comicsdb.models.credits.Credits/Role:**

```python
from comicsdb.models.character import Character
from comicsdb.models.creator import Creator
from comicsdb.models.credits import Credits, Role
```

Used by `ReadingListDetailView.get_context_data()` to compute `featured_creators` (top 6 by issue count, writer/artist roles only) and `top_characters` (top 12 by appearance count) across the list's issues.

**comicsdb.views.mixins.SearchMixin, LazyLoadMixin:**

```python
from comicsdb.views.mixins import LazyLoadMixin, SearchMixin
```

`SearchMixin` provides search functionality for `SearchReadingListListView`; `LazyLoadMixin` backs `ReadingListItemsLoadMore`'s pagination logic.

**comicsdb.filters.reading_list.ReadingListViewFilter:**

```python
from comicsdb.filters.reading_list import ReadingListViewFilter
```

Applied in `ReadingListListView.get_queryset()`.

**users.models.CustomUser:**

```python
from users.models import CustomUser
```

Used for user ownership and permissions.

### External Dependencies

**autocomplete package:**

```python
from autocomplete import ModelAutocomplete, register, widgets
```

Provides autocomplete functionality for issue and arc search.

## Management Commands

### import_reading_lists

**File:** `reading_lists/management/commands/import_reading_lists.py`

**Purpose:** Bulk-import reading lists from JSON files, always assigning ownership to the "Metron" user (this command is for seeding official/curated lists, not general-purpose user import).

**Usage:**

```bash
python manage.py import_reading_lists <path> [<path> ...] [--dry-run] [--skip-missing]
```

- `paths`: One or more JSON files and/or directories (directories are globbed for `*.json`)
- `--dry-run`: Reports what would be created without writing to the database
- `--skip-missing`: Skips issues not found in the database instead of raising a `CommandError`

**JSON Format** (per file — issues are matched by numeric `Issue` primary key, not by series/number lookup):

```json
{
  "name": "[2015-2016] Secret Wars",
  "source": "CBRO",
  "books": [
    {"index": 0, "database": {"id": 12345}},
    {"index": 1, "database": {"id": 12346}}
  ]
}
```

**Behavior:**

1. Requires a `CustomUser` named `"Metron"` to already exist — raises `CommandError` immediately if not
2. `name` is passed through `_sanitize_name()`, which strips a leading `[YYYY]`, `[YYYY-YYYY]`, `(YYYY)`, or `(YYYY-YYYY)` prefix (e.g. `"[2015-2016] Secret Wars"` → `"Secret Wars"`)
3. `source` is mapped to an `AttributionSource` choice via `_get_attribution_source()` (accepts both `"LoCG"` and `"LOCG"` for the League of ComicGeeks source; unrecognized codes silently map to `""`)
4. Skips the whole file (returns `"skipped"`) if a list with that `(user=Metron, name)` already exists
5. Validates every `book["database"]["id"]` exists as an `Issue` via `_validate_issues()` before creating anything — controlled by `--skip-missing`
6. Creates the `ReadingList` (always `is_private=False`) and its `ReadingListItem`s inside `transaction.atomic()`, using `bulk_create()`
7. `order` is set directly from each book's `index` field (0-based, as supplied by the source JSON) — not renumbered to match the app's 1-based `order` convention used elsewhere
8. Duplicate issue IDs within the same file are skipped and reported; does not set `list_type` or `image` (both retain model defaults)

**Use Cases:**

- Seeding the database with official Metron reading orders (from CBRO/CMRO/League of ComicGeeks/etc. exports)
- Bulk-loading curated reading orders ahead of assigning "reading list editor" curation

## API Integration

### REST API Endpoints

The reading lists feature provides read-only REST API endpoints via `ReadingListViewSet` (`api/views.py`), registered at basename `reading_list`. Complete API documentation is available in the main [API README](/api/README.md).

**Available Endpoints:**

- `GET /api/reading_list/` - List reading lists (`ReadingListListSerializer`)
- `GET /api/reading_list/{id}/` - Retrieve reading list details (`ReadingListReadSerializer`); supports conditional requests (`Last-Modified`/`If-Modified-Since`) via `ConditionalRetrieveModelMixin`
- `GET /api/reading_list/{id}/items/` - Paginated reading list items (`ReadingListItemSerializer`, via `@action(detail=True)` named `items`)

**Authentication:**

All reading list API endpoints require authentication.

**Permissions/Visibility (`ReadingListViewSet.get_queryset()`):**

- Unauthenticated: no access (endpoints require authentication)
- Authenticated, non-staff: public lists + own lists
- Staff (`is_staff=True`): public lists + own lists + Metron's lists

Note this differs slightly from the web views' visibility rules: the API queryset only special-cases `is_staff`, not the "reading list editor" group — editor-group members who aren't staff see public + own lists via the API but not Metron's private lists (the web views include the group in that check; see [Visibility Rules](#visibility-rules)).

**API Serializers** (`api/v1_0/serializers/reading_list.py`):

**ReadingListItemSerializer:**

```python
class ReadingListItemSerializer(serializers.ModelSerializer):
    issue = ReadingListIssueSerializer(read_only=True)
    issue_type = serializers.CharField(source="get_issue_type_display", read_only=True)

    class Meta:
        model = ReadingListItem
        fields = ("id", "issue", "order", "issue_type")
```

- `issue`: Nested `ReadingListIssueSerializer` (id, series, number, cover_date, store_date, cv_id, gcd_id, modified — deliberately excludes `image`/`cover_hash` to keep the payload light)
- `issue_type`: Uses `get_issue_type_display()` to return human-readable labels ("Prologue", "Core Issue", "Tie-In", "Epilogue", or empty string)

**ReadingListListSerializer:** `id`, `name`, `slug`, `user`, `list_type` (display label via `get_list_type_display`), `is_private`, `attribution_source`, `average_rating`, `rating_count`, `modified`

**ReadingListReadSerializer:** All of the above plus `desc`, `image`, `attribution_url`, `items_url` (absolute URL to the `items` action), `resource_url` (absolute URL to the web detail page). `attribution_source` here is the display label (`get_attribution_source_display`), unlike the raw code used elsewhere.

**Filtering:**

Backed by `ReadingListFilter` (see [Filters](#filters)) — supports `name`, `user`, `username`, `attribution_source`, `list_type`, `is_private`, `modified_gt`, `average_rating__gte`, and `publisher`:

- `/api/reading_list/?average_rating__gte=4` - Lists with 4+ stars
- `/api/reading_list/?list_type=EVENT` - Event-type lists only
- `/api/reading_list/?modified_gt=2026-01-01T00:00:00Z` - Lists modified since a given timestamp

**Query Annotations:**

`ReadingListViewSet.get_queryset()` annotates:

```python
.annotate(
    average_rating=Avg("ratings__rating"),
    rating_count=Count("ratings", distinct=True),
)
```

For complete API documentation including pagination and response formats, see the [main API documentation](/api/README.md#reading-list).

## Testing

### Test Files

**Files:**

- `tests/reading_lists/test_views.py`
- `tests/reading_lists/test_forms.py`
- `tests/reading_lists/test_models.py`
- `tests/reading_lists/test_signals.py`
- `tests/reading_lists/test_assign_to_metron.py`
- `tests/reading_lists/test_reading_list_editor_group_permissions.py`
- `tests/reading_lists/test_admin_metron_permissions.py`
- `tests/reading_lists/test_api_reading_list.py`
- `tests/reading_lists/test_import_command.py`
- `tests/reading_lists/conftest.py`

### Current Test Coverage

**Test Statistics:**

Run `pytest tests/reading_lists/ --cov` for current pass/fail counts and coverage percentages — they aren't reproduced here since they drift with every change to the app. As a rough sense of scale, the suite currently has on the order of 275+ test functions spread across the files above (`test_views.py` alone accounts for roughly 40% of that).

### Test Coverage by Feature

**Model Tests:**

- ReadingList creation and validation
- Unique constraint enforcement
- Computed properties (start_year, end_year, publishers)
- Slug generation

**View Tests:**

- Permission checks (owner, admin, Metron)
- Queryset filtering (public, private, Metron)
- Form validation
- Issue ordering logic
- **Series bulk addition** (11 tests):
  - Authentication and permissions
  - Adding all issues from series
  - Range filtering (start/end/both)
  - Position handling (beginning/end)
  - Duplicate detection
  - Admin permissions for Metron lists
  - Redirect and success messages
- **Arc bulk addition** (10+ tests):
  - Authentication and permissions
  - Adding all issues from arc
  - Position handling (beginning/end)
  - Duplicate detection
  - "reading list editor" group permissions
  - Admin permissions for Metron lists
- **Group permissions** (`test_reading_list_editor_group_permissions.py`):
  - "reading list editor" group creation (via migration `0002_create_reading_list_editor_group.py`)
  - Permission checks for Metron lists
  - Editor permissions vs admin permissions
  - Attribution field restrictions
- **Admin Metron permissions** (`test_admin_metron_permissions.py`):
  - `ReadingListAdmin`/`ReadingListItemAdmin` behavior for staff vs non-staff/editor users
- **API tests** (`test_api_reading_list.py`):
  - `ReadingListViewSet` list/retrieve visibility rules (public/own/Metron)
  - `items` action pagination
  - Serializer field output (`list_type`, `image`, `items_url`, `resource_url`, display labels)
  - `ReadingListFilter` filtering (`list_type`, `publisher`, `modified_gt`, `average_rating__gte`, etc.)
- **Import command tests** (`test_import_command.py`):
  - JSON parsing, name sanitization, attribution source mapping
  - `--dry-run` and `--skip-missing` behavior
  - Duplicate list and duplicate issue handling
- **Signal tests** (`test_signals.py`):
  - `update_reading_list_modified_on_item_change` bumps `ReadingList.modified` on `ReadingListItem` save and delete
- **Rating system** (comprehensive test suite):
  - Creating ratings (1-5 stars)
  - Updating existing ratings
  - Deleting/clearing ratings
  - Permission checks (cannot rate own lists, private lists)
  - Authentication requirements
  - HTMX endpoint functionality
  - Average rating calculations
  - Rating count aggregations
  - Template rendering with rating data
- **Issue type editing** (13 comprehensive tests):
  - Authentication requirements (login required for all operations)
  - Permission checks (owner/admin/editor access control)
  - Edit form display (HTMX GET endpoint)
  - Setting issue types (all four types: Prologue, Core, Tie-In, Epilogue)
  - Clearing issue types (empty string)
  - Updating issue types (HTMX POST endpoint)
  - Canceling edits (HTMX GET endpoint)
  - Invalid value rejection (non-existent types ignored)
  - Metron list permissions (admin can edit)
  - Metron list permissions (reading list editors can edit)
  - Metron list permissions (regular users cannot edit)
  - Template rendering in display mode
  - Template rendering in edit mode
- **Assign to Metron** (`test_assign_to_metron.py`):
  - Permission checks (staff, "reading list editor" group, regular users, list owners without staff/editor status)
  - Confirm-page rendering and redirect-when-already-Metron-owned behavior
  - Ownership transfer on POST, and no-op behavior when already Metron-owned
  - Anonymous users redirected to login
  - Detail view `can_assign_to_metron` context flag and button visibility
  - Graceful failure when the "Metron" account does not exist
  - Direct tests of the `can_assign_reading_list_to_metron()` helper

**Form Tests:**

- **AddIssuesFromSeriesForm** (13 tests):
  - All issues selection
  - Range validation (with/without numbers)
  - Start/end number combinations
  - Missing required fields
  - Field labels and help text
  - Radio button choices
- **AddIssuesFromArcForm** (5+ tests):
  - Arc selection validation
  - Position field validation
  - Field labels and help text
  - Radio button choices

**Autocomplete Tests:**

- Basic search
- Smart search with `#`
- Empty queries
- Special characters

### Test Fixtures

**Key Fixtures:**

- `series_with_multiple_issues`: Creates a series with 10 sequential issues for bulk testing
- `arc_with_multiple_issues`: Creates an arc with 5 issues across multiple series
- `reading_list_with_issues`: Reading list pre-populated with 3 issues
- `metron_reading_list`: Lists owned by Metron user
- `editor_user`: User in the "reading list editor" group
- `reading_list_item`: A single `ReadingListItem` (used by signal tests)
- Standard user fixtures for permission testing

### Example Test

```python
class ReadingListModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="testuser")
        self.reading_list = ReadingList.objects.create(
            user=self.user,
            name="Test List"
        )

    def test_unique_constraint(self):
        """Test that users cannot create duplicate list names."""
        with self.assertRaises(IntegrityError):
            ReadingList.objects.create(
                user=self.user,
                name="Test List"
            )

    def test_start_year_with_no_issues(self):
        """Test start_year returns None when list is empty."""
        self.assertIsNone(self.reading_list.start_year)
```

## Future Enhancements

### Completed Features

- ✅ **Series Bulk Addition** (Implemented)
  - Add all issues or ranges from a series
  - Chronological ordering by cover date
  - Position control (beginning/end)
  - Duplicate detection

- ✅ **Arc Bulk Addition** (Implemented)
  - Add all issues from a story arc
  - Chronological ordering by cover date
  - Position control (beginning/end)
  - Duplicate detection

- ✅ **Group-Based Permissions** (Implemented)
  - "reading list editor" group
  - Manage Metron user's lists without admin access
  - Curator role for official reading orders

- ✅ **Assign to Metron** (Implemented)
  - Staff and "reading list editor" group members can reassign any reading list's ownership to the "Metron" account
  - Dedicated confirmation page before the (one-way) ownership change
  - Standalone permission check independent of list ownership

- ✅ **Import Management Command** (Implemented)
  - Bulk import from JSON files (always owned by "Metron")
  - Issue matching by ID, name sanitization, attribution source mapping
  - `--dry-run` and `--skip-missing` support

- ✅ **REST API Endpoints** (Implemented)
  - Read-only API access
  - List and retrieve reading lists
  - Access reading list items
  - Permission-based filtering

- ✅ **Community Rating System** (Implemented)
  - 1-5 star ratings for public reading lists
  - Users can rate lists (except their own)
  - Average rating and count display
  - HTMX-powered interactive star component
  - Rating filter for discovery (minimum rating)
  - API integration with rating fields
  - Optimized queries with rating annotations

- ✅ **Issue Type Categorization** (Implemented)
  - Tag issues as Prologue, Core Issue, Tie-In, or Epilogue
  - Optional field with four predefined choices
  - HTMX-powered inline editing interface
  - Colored badges display in web UI
  - Exposed in API serializer
  - Permission-based editing (owners, admins, reading list editors)

- ✅ **List Type Categorization** (Implemented)
  - `list_type` field (Creator, Event, Story, Characters, Teams, Master)
  - Filterable in both the web UI and API
  - Displayed as a tag on list cards

- ✅ **Cover Images** (Implemented)
  - Optional `image` field (`sorl-thumbnail`), same storage pattern as issue covers
  - Displayed on list cards; falls back to a watermark icon when unset

- ✅ **Advanced Search & Filtering** (Implemented)
  - Quick search (`q`) plus a collapsible advanced-filters panel: name, creator/username, publisher, list type, attribution source, minimum rating, privacy
  - Removable filter chips showing currently-active filters
  - Publisher filter runs as a subquery to avoid slow JOIN/aggregate combinations

- ✅ **Lazy-Loaded Item Pagination** (Implemented)
  - Detail page shows the first 50 issues; `ReadingListItemsLoadMore` HTMX-loads 30 more at a time
  - Built on the shared `LazyLoadMixin` used elsewhere in the project

- ✅ **Detail-Page Analytics** (Implemented)
  - Issue-type, series, and publisher breakdowns
  - Featured creators (top 6 by issue count, writer/artist roles)
  - Top characters (top 12 by appearance count)
  - All computed from already-prefetched data, no extra queries

### Planned Features

1. **List Collaboration**
    - Share lists with specific users
    - Collaborative editing permissions
    - Fork/clone existing lists

2. **Progress Tracking**
    - Mark issues as read/unread
    - Reading progress percentage
    - Completion dates

3. **Further Statistics**
    - Estimated reading time
    - Year distribution charts (beyond the current start/end year range)

4. **Rating Enhancements**
    - Written reviews/comments on ratings
    - Rating categories (accuracy, completeness, organization)
    - Helpful/unhelpful votes on ratings

5. **Additional Bulk Operations**
    - Import from CSV/text list
    - Export to various formats (CSV, JSON, plain text)
    - Merge multiple lists
    - Duplicate list functionality

### Possible Technical Improvements

1. **Caching**
    - Cache computed properties
    - Redis for list queries
    - Template fragment caching

2. **Async Operations**
    - Celery task queue for long-running operations
    - Progress notifications

3. **Search Enhancements**
    - Full-text search with PostgreSQL (`unaccent`/trigram indexes are used elsewhere in `comicsdb`, but not yet on `ReadingList.name`)
    - Elasticsearch integration

4. **Performance**
    - Denormalize issue counts
    - Materialized views for complex queries
    - Query result pagination improvements
