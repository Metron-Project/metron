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
- [API Integration](#api-integration)
- [Testing](#testing)
- [Future Enhancements](#future-enhancements)

## Architecture Overview

The reading_lists app follows Django's MTV (Model-Template-View) pattern with:

- **Models**: `ReadingList`, `ReadingListItem` (through model), and `ReadingListRating`
- **Views**: Class-based views (CBVs) for all operations, plus HTMX-powered rating view
- **Forms**: Django forms with autocomplete integration
- **Permissions**: Mixin-based permission checks

**Key Dependencies:**

- Django's class-based views
- `autocomplete` package for issue search
- `comicsdb` app for Issue and Publisher models
- `users` app for CustomUser model

## Models

### ReadingList

The main model for user-created reading lists.

**File:** `reading_lists/models.py`

```python
class ReadingList(CommonInfo):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    is_private = models.BooleanField(default=False)
    attribution_source = models.CharField(max_length=10, choices=AttributionSource.choices)
    attribution_url = models.URLField(blank=True)
    issues = models.ManyToManyField(Issue, through="ReadingListItem")
```

**Inherited Fields from CommonInfo:**

- `name`: CharField with max_length from CommonInfo
- `slug`: Auto-generated from name via pre_save signal
- `desc`: TextField for description
- `cv_id`: ComicVine ID (optional)
- `gcd_id`: Grand Comics Database ID (optional)
- `created_on`: Auto-generated creation timestamp
- `modified`: Auto-updated modification timestamp

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

**Constraints:**

- Unique together: `(user, name)` - prevents duplicate list names per user
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
    reading_list = models.ForeignKey(ReadingList, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
```

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

All views are class-based views (CBVs) inheriting from Django's generic views.

**File:** `reading_lists/views.py`

### Public Views

#### ReadingListListView
```python
class ReadingListListView(ListView):
    model = ReadingList
    template_name = "reading_lists/readinglist_list.html"
    paginate_by = 30
```

**Queryset Logic:**

- Unauthenticated: Only public lists
- Authenticated non-admin: Public lists + user's own lists
- Admin: Public lists + user's own lists + Metron's lists

**Annotations:**

- `issue_count`: Count of issues in the list
- `average_rating`: Average of all ratings for the list
- `rating_count`: Total number of ratings for the list

**URL:** `/reading-lists/`

#### SearchReadingListListView
```python
class SearchReadingListListView(SearchMixin, ReadingListListView):
    def get_search_fields(self):
        return ["name__icontains", "user__username__icontains", "attribution_source__icontains"]
```

Inherits queryset filtering from `ReadingListListView`.

**URL:** `/reading-lists/search/`

#### ReadingListDetailView
```python
class ReadingListDetailView(DetailView):
    model = ReadingList
    template_name = "reading_lists/readinglist_detail.html"
```

**Context Data:**

- `reading_list_items`: Prefetched and ordered by `order` field (limited to first 50 for pagination)
- `reading_list_items_count`: Total count of items in the list
- `is_owner`: Boolean indicating if user can edit (owner or admin managing Metron)
- `user_rating`: User's own rating (if authenticated and has rated)
- `average_rating`: Average rating from all users (annotated)
- `rating_count`: Total number of ratings (annotated)
- `start_year`: Earliest cover date year (annotated, not property)
- `end_year`: Latest cover date year (annotated, not property)
- `publishers`: Unique publishers extracted from prefetched data

**Query Optimizations:**

The detail view is heavily optimized to reduce database queries:

1. **Prefetch reading list items** with related issue, series, publisher data
2. **Annotate year ranges** instead of using expensive properties
3. **Prefetch and annotate ratings** to avoid N+1 queries
4. **Extract publishers from prefetched data** instead of separate query
5. **Result**: Reduced from ~20 queries to 4-6 queries per page load

**URL:** `/reading-lists/<slug>/`

### Authenticated Views

#### UserReadingListListView
```python
class UserReadingListListView(LoginRequiredMixin, ListView):
    model = ReadingList
    template_name = "reading_lists/user_readinglist_list.html"
    paginate_by = 30

    def get_queryset(self):
        return ReadingList.objects.filter(user=self.request.user)
```

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
        reading_list = self.get_object()
        is_owner = reading_list.user == self.request.user
        is_admin_managing_metron = (
            self.request.user.is_staff and
            reading_list.user.username == "Metron"
        )
        return is_owner or is_admin_managing_metron
```

**URL:** `/reading-lists/<slug>/update/`

#### ReadingListDeleteView
```python
class ReadingListDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ReadingList
    success_url = reverse_lazy("reading-list:my-lists")
```

Uses same `test_func()` as UpdateView.

**URL:** `/reading-lists/<slug>/delete/`

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
    path("<slug:slug>/add-issue/", AddIssueWithAutocompleteView.as_view(), name="add-issue"),
    path("<slug:slug>/add-from-series/", AddIssuesFromSeriesView.as_view(), name="add-from-series"),
    path("<slug:slug>/add-from-arc/", AddIssuesFromArcView.as_view(), name="add-from-arc"),
    path("<slug:slug>/remove-issue/<int:item_pk>/", RemoveIssueFromReadingListView.as_view(), name="remove-issue"),
    path("<slug:slug>/rate/", update_reading_list_rating, name="rate"),
]
```

## Forms

**File:** `reading_lists/forms.py`

### ReadingListForm

```python
class ReadingListForm(forms.ModelForm):
    class Meta:
        model = ReadingList
        fields = ("name", "desc", "is_private", "attribution_source", "attribution_url")
```

**Dynamic Field Removal:**
Attribution fields are removed in view's `get_form()` for non-admin users.

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

The app uses `UserPassesTestMixin` for permission checks rather than object-level permissions.

**Base Permission Check:**
```python
def test_func(self):
    reading_list = self.get_object()
    is_owner = reading_list.user == self.request.user

    # Check if user is in Reading List Editor group
    is_editor = self.request.user.groups.filter(name="Reading List Editor").exists()
    can_manage_metron = is_editor and reading_list.user.username == "Metron"

    # Admin can also manage Metron lists
    is_admin_managing_metron = (
        self.request.user.is_staff and
        reading_list.user.username == "Metron"
    )

    return is_owner or can_manage_metron or is_admin_managing_metron
```

**Reading List Editor Group:**

A Django group created via migration that provides special permissions for managing Metron user's reading lists.

**Migration:** `0002_create_reading_list_editor_group.py`

**Purpose:**

- Allows designated curators to manage official reading orders
- Provides elevated permissions without full admin access
- Separates content curation from system administration

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

**Reading List Editor Group:**

- All authenticated permissions
- Can edit/delete Metron user's lists
- Can view Metron's private lists
- Cannot set attribution fields (admin-only)

**Admin Users (is_staff=True):**

- All authenticated permissions
- Can edit/delete Metron user's lists
- Can view Metron's private lists
- Can set attribution fields

### Visibility Rules

Implemented in queryset filtering:

```python
def get_queryset(self):
    queryset = ReadingList.objects.all()

    if not self.request.user.is_authenticated:
        return queryset.filter(is_private=False)

    if self.request.user.is_staff:
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

### ReadingListFilter (API Filter)

Django filter for API endpoints.

```python
class ReadingListFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    user = filters.NumberFilter(field_name="user__id")
    username = filters.CharFilter(field_name="user__username", lookup_expr="icontains")
    attribution_source = filters.CharFilter(lookup_expr="icontains")
    is_private = filters.BooleanFilter()
    modified_gt = filters.DateTimeFilter(field_name="modified", lookup_expr="gt")
    average_rating__gte = filters.NumberFilter(
        field_name="average_rating",
        lookup_expr="gte",
        label="Minimum Rating",
    )
```

**Fields:**

- `name`: Case-insensitive search on list name
- `user`: Filter by user ID
- `username`: Case-insensitive search on username
- `attribution_source`: Filter by attribution source
- `is_private`: Filter by privacy status
- `modified_gt`: Filter by modification date (greater than)
- `average_rating__gte`: Filter by minimum average rating (1-5)

### ReadingListViewFilter (Web View Filter)

Django filter for web views with search functionality.

```python
class ReadingListViewFilter(df.FilterSet):
    q = df.CharFilter(method="filter_search", label="Search")
    name = df.CharFilter(lookup_expr="icontains", label="Name")
    username = df.CharFilter(field_name="user__username", lookup_expr="icontains", label="Username")
    attribution_source = df.CharFilter(lookup_expr="icontains", label="Source")
    is_private = df.BooleanFilter(label="Private")
    average_rating__gte = df.NumberFilter(
        field_name="average_rating",
        lookup_expr="gte",
        label="Minimum Rating",
    )
```

**Features:**

- `q`: Global search across name, username, and attribution source
- Individual field filters for precise searching
- Rating filter for quality-based discovery
- Integrated with `ReadingListListView` and `SearchReadingListListView`

**Rating Filter Options:**

The web interface provides a dropdown with:
- All Ratings (no filter)
- 1+ Stars
- 2+ Stars
- 3+ Stars
- 4+ Stars
- 5 Stars

**Filter Template:** `partials/readinglist_filter.html`

## Templates

**Directory:** `reading_lists/templates/reading_lists/`

### Template Files

| Template | Purpose | Key Features |
|----------|---------|--------------|
| `readinglist_list.html` | List all public lists | Pagination, search link, issue counts |
| `user_readinglist_list.html` | User's own lists | Create button, edit/delete links |
| `readinglist_detail.html` | Single list detail | Ordered issues, add/remove controls, bulk add button |
| `readinglist_form.html` | Create/edit form | Dynamic field visibility |
| `readinglist_confirm_delete.html` | Delete confirmation | Issue count warning |
| `add_issue_autocomplete.html` | Add issues interface | Autocomplete, drag-drop, preview |
| `add_issues_from_series.html` | Bulk add from series | Series autocomplete, HTMX range toggle, usage tips |
| `add_issues_from_arc.html` | Bulk add from arc | Arc autocomplete, position selection, usage tips |
| `remove_issue_confirm.html` | Remove issue confirmation | Issue details |
| `partials/reading_list_rating.html` | Rating component | HTMX-powered star rating, average display |

### Template Context

**Common Context Variables:**

- `reading_list`: ReadingList instance
- `reading_list_items`: Ordered queryset of ReadingListItem
- `is_owner`: Boolean for edit permissions
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

## Database Optimization

### QuerySet Optimizations

**List Views:**
```python
queryset = ReadingList.objects.select_related("user").annotate(
    issue_count=Count("issues"),
    average_rating=Avg("ratings__rating"),
    rating_count=Count("ratings", distinct=True),
)
```

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
- **Year Range Annotations**: Replaces expensive property calls with database aggregation
- **Publisher Extraction**: Extracted from prefetched data instead of separate query

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

- `ReadingList`: `(user, name)` - prevents duplicate list names per user
- `ReadingListItem`: `(reading_list, issue)` - prevents duplicate issues in a list
- `ReadingListRating`: `(reading_list, user)` - one rating per user per list

**Benefits:**

- Prevents duplicate data at database level
- Faster lookups on constrained fields
- Data integrity enforcement
- Enables `update_or_create()` for idempotent rating updates

## API Integration

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
Used in `publishers` property for aggregation.

**comicsdb.views.mixins.SearchMixin:**
```python
from comicsdb.views.mixins import SearchMixin
```
Provides search functionality for `SearchReadingListListView`.

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

**Purpose:** Import reading lists from JSON files for bulk data import.

**Usage:**
```bash
python manage.py import_reading_lists <json_file>
```

**JSON Format:**
```json
{
  "reading_lists": [
    {
      "name": "Secret Wars (2015)",
      "description": "Complete reading order for Secret Wars event",
      "is_private": false,
      "attribution_source": "CBRO",
      "attribution_url": "https://example.com/reading-order",
      "issues": [
        {"series": "Secret Wars", "number": "1"},
        {"series": "Amazing Spider-Man", "number": "1"}
      ]
    }
  ]
}
```

**Features:**

- Batch import of multiple reading lists
- Automatic issue matching by series name and number
- Duplicate detection and skipping
- Attribution source validation
- Progress reporting
- Error handling and validation

**Use Cases:**

- Migrating reading lists from other systems
- Bulk importing curated reading orders
- Seeding database with official Metron reading lists
- Backing up and restoring reading lists

## API Integration

### REST API Endpoints

The reading lists feature provides read-only REST API endpoints. Complete API documentation is available in the main [API README](/api/README.md).

**Available Endpoints:**

- `GET /api/reading_list/` - List reading lists
- `GET /api/reading_list/{id}/` - Retrieve reading list details
- `GET /api/reading_list/{id}/reading_list_item_list/` - Get reading list items

**Authentication:**

All reading list API endpoints require authentication.

**Permissions:**

- Authenticated users can access public lists and their own lists
- Admin and Reading List Editor users can access Metron's lists

**API Serializers:**

**ReadingListListSerializer:**
- Includes `average_rating` (FloatField, read-only)
- Includes `rating_count` (IntegerField, read-only)

**ReadingListReadSerializer:**
- Includes `average_rating` (FloatField, read-only)
- Includes `rating_count` (IntegerField, read-only)

**Filtering:**

The API supports filtering by `average_rating__gte` (minimum rating):
- `/api/reading_list/?average_rating__gte=4` - Lists with 4+ stars

**Query Annotations:**

All API views annotate reading lists with:
```python
.annotate(
    average_rating=Avg("ratings__rating"),
    rating_count=Count("ratings", distinct=True),
)
```

For complete API documentation including filtering, pagination, and response formats, see the [main API documentation](/api/README.md#reading-list).

## Testing

### Test Files

**Files:**

- `tests/reading_lists/test_views.py`
- `tests/reading_lists/test_forms.py`
- `tests/reading_lists/test_models.py`
- `tests/reading_lists/conftest.py`

### Current Test Coverage

**Test Statistics:**

- Total tests: 150+ passing
- Forms: 100% coverage
- Views: 95% coverage
- Models: 100% coverage

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
    - Reading List Editor group permissions
    - Admin permissions for Metron lists
- **Group permissions** (comprehensive test suite):
    - Reading List Editor group creation
    - Permission checks for Metron lists
    - Editor permissions vs admin permissions
    - Attribution field restrictions
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
- `editor_user`: User in Reading List Editor group
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
    - Reading List Editor group
    - Manage Metron user's lists without admin access
    - Curator role for official reading orders

- ✅ **Import Management Command** (Implemented)
    - Bulk import from JSON files
    - Issue matching and validation
    - Progress reporting

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

### Planned Features

1. **List Collaboration**
    - Share lists with specific users
    - Collaborative editing permissions
    - Fork/clone existing lists

2. **Progress Tracking**
    - Mark issues as read/unread
    - Reading progress percentage
    - Completion dates

3. **Enhanced Statistics**
    - Estimated reading time
    - Publisher breakdowns
    - Year distribution charts

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
    - Full-text search with PostgreSQL
    - Elasticsearch integration
    - Advanced filtering

4. **Performance**
    - Denormalize issue counts
    - Materialized views for complex queries
    - Query result pagination improvements

