# User Collection - Technical Documentation

Developer documentation for the `user_collection` Django app.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Models](#models)
- [Views and URLs](#views-and-urls)
- [Forms](#forms)
- [Filters](#filters)
- [HTMX Integration](#htmx-integration)
- [Autocomplete](#autocomplete)
- [Templates](#templates)
- [Database Optimization](#database-optimization)
- [API Integration](#api-integration)
- [Privacy and Security](#privacy-and-security)
- [Testing](#testing)
- [Future Enhancements](#future-enhancements)

## Architecture Overview

The user_collection app follows Django's MTV (Model-Template-View) pattern with:

- **Models**: `CollectionItem` for tracking user collections
- **Views**: Class-based views (CBVs) for all operations
- **Forms**: Django forms with autocomplete and custom widgets
- **Filters**: Django-filter integration for advanced filtering
- **HTMX**: Real-time star rating updates

**Key Dependencies:**

- Django's class-based views
- `autocomplete` package for issue search
- `django-filter` for advanced filtering
- `django-money` for currency fields
- `comicsdb` app for Issue, Series, Publisher models
- `users` app for CustomUser model
- HTMX for dynamic rating updates

**Privacy Model:**

- Collections are strictly private - users can only access their own items
- No public/private toggle - all collections are private by default
- Read-only API access available for authenticated users

## Models

### CollectionItem

The main model for tracking comic book ownership and metadata.

**File:** `user_collection/models.py`

```python
class CollectionItem(models.Model):
    # Relationships
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE)

    # Collection metadata
    quantity = models.PositiveSmallIntegerField(default=1)
    book_format = models.CharField(max_length=10, choices=BookFormat.choices)

    # Grading
    grade = models.DecimalField(max_digits=3, decimal_places=1, choices=GRADE_CHOICES)
    grading_company = models.CharField(max_length=10, choices=GradingCompany.choices)

    # Purchase information
    purchase_date = models.DateField(null=True, blank=True)
    purchase_price = MoneyField(max_digits=7, decimal_places=2)
    purchase_store = models.CharField(max_length=255, blank=True)

    # Storage and notes
    storage_location = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    # Reading tracking
    is_read = models.BooleanField(default=False)
    date_read = models.DateTimeField(null=True, blank=True)  # Changed from DateField for precise scrobble tracking
    rating = models.PositiveSmallIntegerField(null=True, choices=[(i, i) for i in range(1, 6)])

    # Timestamps
    created_on = models.DateTimeField(db_default=Now())
    modified = models.DateTimeField(auto_now=True)
```

**Choice Fields:**

```python
class BookFormat(models.TextChoices):
    PRINT = "PRINT", "Print"
    DIGITAL = "DIGITAL", "Digital"
    BOTH = "BOTH", "Both"

class GradingCompany(models.TextChoices):
    CGC = "CGC", "CGC (Certified Guaranty Company)"
    CBCS = "CBCS", "CBCS (Comic Book Certification Service)"
    PGX = "PGX", "PGX (Professional Grading Experts)"
```

**Grade Choices:**

Uses the standard CGC 10-point grading scale:

```python
GRADE_CHOICES = [
    (Decimal("10.0"), "10.0 (Gem Mint)"),
    (Decimal("9.9"), "9.9 (Mint)"),
    (Decimal("9.8"), "9.8 (NM/M - Near Mint/Mint)"),
    # ... continues down to ...
    (Decimal("0.5"), "0.5 (PR - Poor)"),
]
```

**Constraints:**

- Unique together: `(user, issue)` - prevents duplicate issues in a user's collection
- Indexes:
    - `(user, issue)` - primary lookup index
    - `(user, purchase_date)` - for purchase date filtering
    - `(user, book_format)` - for format filtering
    - `(user, is_read)` - for read status filtering
    - `(user, grade)` - for grade filtering
    - `(user, grading_company)` - for grading company filtering

**Meta Options:**

```python
class Meta:
    ordering = ["user", "issue__series__sort_name", "issue__cover_date"]
    unique_together = ["user", "issue"]
    verbose_name = "Collection Item"
    verbose_name_plural = "Collection Items"
```

**Methods:**

- `get_absolute_url()`: Returns detail view URL using primary key
- `__str__()`: Returns formatted string with username, issue, and quantity

**Field Details:**

- `quantity`: Tracks multiple copies of the same issue
- `book_format`: Distinguishes physical, digital, and hybrid ownership
- `grade`: Optional grading on CGC scale (0.5 to 10.0)
- `grading_company`: Optional - blank means user-assessed grade
- `purchase_price`: MoneyField with currency support
- `rating`: 1-5 star rating system for personal tracking
- `is_read`: Boolean for reading progress tracking
- `date_read`: Optional timestamp of when issue was read (DateTimeField for precise scrobble tracking)

## Views and URLs

All views are class-based views (CBVs) with `LoginRequiredMixin` for authentication.

**File:** `user_collection/views.py`

### CollectionListView

```python
class CollectionListView(LoginRequiredMixin, ListView):
    model = CollectionItem
    template_name = "user_collection/collection_list.html"
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
        filtered = CollectionViewFilter(self.request.GET, queryset=queryset)
        return filtered.qs
```

**Features:**

- User-scoped queryset (only own items)
- Advanced filtering via `CollectionViewFilter`
- Optimized with `select_related()` for series data
- Pagination (50 items per page)
- Filter context for template

**URL:** `/collection/`

### CollectionDetailView

```python
class CollectionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = CollectionItem
    template_name = "user_collection/collection_detail.html"

    def test_func(self):
        item = self.get_object()
        return item.user == self.request.user
```

**Features:**

- Permission check via `UserPassesTestMixin`
- Only owner can view
- Optimized queryset with `select_related()`
- Shows full item details including cover image

**URL:** `/collection/<pk>/`

### CollectionCreateView

```python
class CollectionCreateView(LoginRequiredMixin, CreateView):
    model = CollectionItem
    form_class = CollectionItemForm
    template_name = "user_collection/collection_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Item added to your collection!")
        return super().form_valid(form)
```

**Features:**

- Passes user to form for duplicate validation
- Auto-sets user on save
- Success message feedback
- Redirects to collection list

**URL:** `/collection/add/`

### CollectionUpdateView

```python
class CollectionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = CollectionItem
    form_class = CollectionItemForm

    def test_func(self):
        item = self.get_object()
        return item.user == self.request.user
```

**Features:**

- Owner-only access via `test_func()`
- Same form as create view
- Passes user for validation
- Success message on update

**URL:** `/collection/<pk>/update/`

### CollectionDeleteView

```python
class CollectionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = CollectionItem
    template_name = "user_collection/collection_confirm_delete.html"
    success_url = reverse_lazy("user_collection:list")

    def test_func(self):
        item = self.get_object()
        return item.user == self.request.user
```

**Features:**

- Owner-only deletion
- Confirmation template
- Success message
- Redirects to collection list

**URL:** `/collection/<pk>/delete/`

### CollectionStatsView

```python
class CollectionStatsView(LoginRequiredMixin, TemplateView):
    template_name = "user_collection/collection_stats.html"

    def get_context_data(self, **kwargs):
        queryset = CollectionItem.objects.filter(user=self.request.user)

        # Calculate statistics
        total_items = queryset.count()
        total_quantity = queryset.aggregate(Sum("quantity"))["quantity__sum"] or 0
        total_value = queryset.aggregate(Sum("purchase_price"))["purchase_price__sum"]
        read_count = queryset.filter(is_read=True).count()
        unread_count = queryset.filter(is_read=False).count()
        format_counts = queryset.values("book_format").annotate(count=Count("id"))
        top_series = (
            queryset.values("issue__series__name", "issue__series__id")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        context.update({
            "total_items": total_items,
            "total_quantity": total_quantity,
            "total_value": total_value or 0,
            "read_count": read_count,
            "unread_count": unread_count,
            "format_counts": format_counts,
            "top_series": top_series,
        })
```

**Statistics Provided:**

- **Total Items**: Unique collection entries
- **Total Quantity**: Sum of all copies (includes quantity field)
- **Total Value**: Sum of all purchase prices
- **Read Count**: Number of read issues
- **Unread Count**: Number of unread issues
- **Format Breakdown**: Count by print/digital/both
- **Top 10 Series**: Most collected series by issue count

**URL:** `/collection/stats/`

### AddIssuesFromSeriesView

```python
class AddIssuesFromSeriesView(LoginRequiredMixin, FormView):
    form_class = AddIssuesFromSeriesForm
    template_name = "user_collection/add_issues_from_series.html"
    success_url = reverse_lazy("user_collection:list")
```

**Purpose:** Bulk addition of issues from a series to a user's collection.

**Complex Logic:**

1. Fetches all issues from selected series ordered by cover date
2. Applies optional range filtering (start/end issue numbers)
3. Filters out duplicate issues already in collection
4. Creates collection items with default format and read status
5. Uses `bulk_create()` for efficient database operations
6. Provides detailed feedback (added count, skipped count)

**Range Filtering:**

- **All issues**: Adds entire series run
- **Start + End**: Adds issues between specified numbers (inclusive)
- **Start only**: Adds from start number to series end
- **End only**: Adds from series beginning to end number

**Default Options:**

- **Default Format**: Applied to all issues (PRINT, DIGITAL, BOTH)
- **Mark as Read**: Optionally mark all added issues as read

**Performance Optimizations:**

- Uses `bulk_create()` for batch insertion
- Single query to fetch existing issue IDs
- List comprehension for building items
- Ordered queryset reduces database work

**Feedback:**

```python
# Example success messages:
"Added 50 issues to your collection! Skipped 5 issues already in your collection."
"Added 100 issues to your collection (marked as read)!"
"All issues from this series are already in your collection."
```

**URL:** `/collection/add-from-series/`

### MissingIssuesListView

```python
class MissingIssuesListView(LoginRequiredMixin, ListView):
    model = Series
    template_name = "user_collection/missing_issues_list.html"
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user
        return (
            Series.objects.annotate(
                total_issues=Count("issues", distinct=True),
                owned_issues=Count(
                    "issues", filter=Q(issues__in_collections__user=user), distinct=True
                ),
            )
            .annotate(missing_count=F("total_issues") - F("owned_issues"))
            .filter(owned_issues__gt=0, missing_count__gt=0)
            .select_related("publisher", "series_type", "imprint")
            .order_by("-missing_count", "sort_name")
        )
```

**Purpose:** Identify gaps in user's collection by showing series where they own some issues but not all.

**Complex Query Logic:**

1. Annotates each series with:
   - `total_issues`: Total number of issues in the series
   - `owned_issues`: Number of issues the user owns from this series
   - `missing_count`: Calculated as total - owned
2. Filters to only show series where:
   - User owns at least one issue (`owned_issues__gt=0`)
   - User is missing at least one issue (`missing_count__gt=0`)
3. Orders by missing count (descending) to prioritize nearly-complete series

**Features:**

- Shows only series the user has started collecting
- Pagination (50 series per page)
- Optimized with `select_related()` for publisher/series type data
- Includes completion statistics for each series
- Color-coded progress bars in template (red/yellow/green)

**Use Cases:**

- Identify incomplete series runs
- Prioritize which series to complete
- Track collection completion progress
- Plan purchases for missing issues

**URL:** `/collection/missing/`

### MissingIssuesDetailView

```python
class MissingIssuesDetailView(LoginRequiredMixin, ListView):
    model = Issue
    template_name = "user_collection/missing_issues_detail.html"
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
```

**Purpose:** Show specific missing issues for a series to help users complete their collection.

**Query Strategy:**

1. First query: Get IDs of all issues the user owns from this series
2. Second query: Get all issues from the series NOT in the owned list
3. Orders by cover date and issue number for chronological viewing

**Context Data:**

- `series`: The series object
- `total_issues`: Total issues in the series
- `owned_issues`: Number of issues user owns
- `missing_count`: Number of issues user doesn't own
- `completion_percentage`: Percentage of series owned (rounded to 1 decimal)
- `missing_issues`: Queryset of missing Issue objects

**Features:**

- Chronological listing of missing issues
- Shows issue number, cover date, and title
- Series completion statistics
- Pagination for long series runs
- Optimized with `select_related()` for series data

**Use Cases:**

- Generate shopping lists for comic stores
- Identify specific gaps in series runs
- Track which issues to acquire next
- Plan purchases by cover date or issue number

**URL:** `/collection/missing/<int:series_id>/`

### update_rating

```python
@login_required
@require_POST
def update_rating(request, pk):
    """HTMX view to update the rating of a collection item."""
    item = get_object_or_404(CollectionItem, pk=pk, user=request.user)

    rating_value = request.POST.get("rating")
    if rating_value:
        try:
            rating = int(rating_value)
            if MIN_RATING <= rating <= MAX_RATING:  # 1-5
                item.rating = rating
            elif rating == 0:  # Clear rating
                item.rating = None
            item.save(update_fields=["rating"])
        except ValueError:
            pass

    return render(request, "user_collection/partials/star_rating.html", {"item": item})
```

**Features:**

- HTMX endpoint for real-time updates
- Function-based view for simplicity
- Owner-only access via `get_object_or_404`
- Rating range validation (1-5)
- Supports clearing rating (value=0)
- Returns partial template for swap
- Uses `update_fields` for efficiency

**URL:** `/collection/<pk>/rate/`

### scrobble (API ViewSet Action)

```python
@action(detail=False, methods=["post"])
def scrobble(self, request):
    """
    Mark an issue as read with optional rating and date_read.

    If the issue is not in the user's collection, it will be automatically
    added with quantity=1 and is_read=True.

    If the issue is already in the collection, the read status and date will
    be updated.

    Returns:
    - 201: Created new collection item
    - 200: Updated existing collection item
    - 400: Validation error
    - 404: Issue not found
    """
```

**File:** `api/views.py` (CollectionViewSet)

**Purpose:** Quick scrobble endpoint for marking issues as read via API.

**Request Body:**

```python
{
    "issue_id": int,              # Required
    "date_read": datetime,        # Optional, defaults to timezone.now()
    "rating": int                 # Optional, 1-5
}
```

**Features:**

- **Auto-creation**: Creates collection item if issue not owned
- **Auto-update**: Updates existing collection items
- **Precise timestamps**: Uses DateTimeField for exact read time
- **Default values**: Sets reasonable defaults for auto-created items
- **User-scoped**: Automatically filtered to request.user

**Auto-Creation Defaults:**

When creating a new collection item via scrobble:

```python
defaults={
    "quantity": 1,
    "book_format": CollectionItem.BookFormat.DIGITAL,
    "is_read": True,
    "date_read": date_read,
    "rating": rating,
}
```

**Update Logic:**

When updating an existing item:

```python
collection_item.is_read = True
collection_item.date_read = date_read
if rating is not None:
    collection_item.rating = rating
collection_item.save()
```

**Response:**

Uses `ScrobbleResponseSerializer` with additional `created` flag:

```python
{
    "id": int,
    "issue": {
        "id": int,
        "series_name": str,
        "number": str
    },
    "is_read": bool,
    "date_read": datetime,
    "rating": int|null,
    "created": bool,      # True if new, False if updated
    "modified": datetime
}
```

**Status Codes:**

- `201 Created`: New collection item was created
- `200 OK`: Existing collection item was updated
- `400 Bad Request`: Validation error (invalid issue_id, rating out of range)
- `404 Not Found`: Issue with specified ID doesn't exist

**Use Cases:**

- Mobile reading apps marking issues as read
- Browser extensions for one-click scrobbling
- Bulk import of reading history
- Integration with external reading trackers

**Security:**

- Requires authentication (IsAuthenticated permission)
- User-scoped (can only scrobble to own collection)
- Issue validation via serializer
- Rating range validation (1-5)

**Performance:**

- Single `get_or_create()` query
- Minimal fields updated on existing items
- No unnecessary eager loading

**URL:** `POST /api/collection/scrobble/`

### URL Configuration

**File:** `user_collection/urls.py`

```python
app_name = "user_collection"
urlpatterns = [
    path("", CollectionListView.as_view(), name="list"),
    path("add/", CollectionCreateView.as_view(), name="create"),
    path("add-from-series/", AddIssuesFromSeriesView.as_view(), name="add-from-series"),
    path("stats/", CollectionStatsView.as_view(), name="stats"),
    path("missing/", MissingIssuesListView.as_view(), name="missing-list"),
    path("missing/<int:series_id>/", MissingIssuesDetailView.as_view(), name="missing-detail"),
    path("<int:pk>/", CollectionDetailView.as_view(), name="detail"),
    path("<int:pk>/update/", CollectionUpdateView.as_view(), name="update"),
    path("<int:pk>/delete/", CollectionDeleteView.as_view(), name="delete"),
    path("<int:pk>/rate/", update_rating, name="rate"),
]
```

## Forms

**File:** `user_collection/forms.py`

### CollectionItemForm

```python
class CollectionItemForm(forms.ModelForm):
    class Meta:
        model = CollectionItem
        fields = (
            "issue", "quantity", "book_format", "grade", "grading_company",
            "purchase_date", "purchase_price", "purchase_store",
            "storage_location", "notes", "is_read", "date_read",
        )
```

**Custom Widgets:**

- **Issue**: `AutocompleteWidget` with `IssueAutocomplete`
- **Purchase Date**: HTML5 date input with Bulma calendar
- **Date Read**: HTML5 date input with Bulma calendar
- **Purchase Price**: `BulmaMoneyWidget` for currency formatting
- **Quantity**: Number input with min=1
- **Notes**: Textarea with 4 rows

**Custom Validation:**

```python
def clean_issue(self):
    """Validate that the issue isn't already in the user's collection."""
    issue = self.cleaned_data.get("issue")

    # Only validate on create (not update)
    if (not self.instance.pk and self.user and issue and
        CollectionItem.objects.filter(user=self.user, issue=issue).exists()):
        raise forms.ValidationError("This issue is already in your collection.")

    return issue
```

**User Context:**

```python
def __init__(self, *args, **kwargs):
    self.user = kwargs.pop("user", None)
    super().__init__(*args, **kwargs)
```

The form requires user context for duplicate validation.

**Help Text:**

Extensive help text for all fields:
- "Comic book condition grade (CGC scale)"
- "Professional grading company (leave blank if user-assessed)"
- "Number of copies you own"
- "Where is it stored?"

### AddIssuesFromSeriesForm

```python
class AddIssuesFromSeriesForm(forms.Form):
    RANGE_CHOICES = [
        ("all", "All issues"),
        ("range", "Issue range"),
    ]

    series = forms.ModelChoiceField(
        queryset=Series.objects.select_related("series_type").all(),
        widget=widgets.AutocompleteWidget(ac_class=SeriesAutocomplete),
    )

    range_type = forms.ChoiceField(
        choices=RANGE_CHOICES,
        initial="all",
        widget=forms.RadioSelect(),
    )

    start_number = forms.CharField(max_length=25, required=False)
    end_number = forms.CharField(max_length=25, required=False)

    default_format = forms.ChoiceField(
        choices=CollectionItem.BookFormat.choices,
        initial=CollectionItem.BookFormat.PRINT,
        required=False,
    )

    mark_as_read = forms.BooleanField(required=False, initial=False)
```

**Features:**

- **Series autocomplete**: Efficient series search
- **Radio buttons**: HTMX-based toggle for range fields
- **Flexible range**: Optional start/end issue numbers
- **Default format**: Applied to all issues in bulk
- **Mark as read**: Bulk reading status update
- **Help text**: Guidance for each field

**Use Case:**

Designed for quickly adding entire series runs to collection:
- Complete series (1-500+ issues)
- Partial runs (e.g., issues 1-100)
- From specific issue onward (e.g., 50-end)
- Up to specific issue (e.g., 1-50)

### ScrobbleRequestSerializer

**File:** `api/v1_0/serializers/collection.py`

```python
class ScrobbleRequestSerializer(serializers.Serializer):
    issue_id = serializers.IntegerField()
    date_read = serializers.DateTimeField(required=False, allow_null=True)
    rating = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5)

    def validate_issue_id(self, value):
        """Verify issue exists."""
        try:
            Issue.objects.get(pk=value)
        except Issue.DoesNotExist as err:
            raise serializers.ValidationError(f"Issue with id {value} does not exist.") from err
        return value
```

**Purpose:** Validates scrobble request data.

**Fields:**

- `issue_id`: Required integer, validated to ensure issue exists
- `date_read`: Optional datetime, defaults to `timezone.now()` in view
- `rating`: Optional integer with range validation (1-5)

**Validation:**

- `issue_id` must reference existing Issue object
- `rating` must be between 1 and 5 (inclusive)
- Both optional fields can be null

### ScrobbleResponseSerializer

**File:** `api/v1_0/serializers/collection.py`

```python
class ScrobbleResponseSerializer(serializers.ModelSerializer):
    issue = CollectionIssueSerializer(read_only=True)
    created = serializers.BooleanField(read_only=True)

    class Meta:
        model = CollectionItem
        fields = (
            "id",
            "issue",
            "is_read",
            "date_read",
            "rating",
            "created",
            "modified",
        )
```

**Purpose:** Serializes scrobble response with minimal fields.

**Features:**

- **Nested issue**: Uses `CollectionIssueSerializer` for issue details
- **Created flag**: Indicates if item was created (True) or updated (False)
- **Minimal fields**: Only includes scrobble-relevant data
- **Read-only**: All fields read-only (no write operations)

**Response Format:**

```json
{
  "id": 123,
  "issue": {
    "id": 456,
    "series_name": "Amazing Spider-Man",
    "number": "1"
  },
  "is_read": true,
  "date_read": "2026-01-08T14:30:00Z",
  "rating": 5,
  "created": true,
  "modified": "2026-01-08T14:30:00Z"
}
```

## Filters

### CollectionFilter (API)

**File:** `comicsdb/filters/collection.py`

```python
class CollectionFilter(filters.FilterSet):
    book_format = filters.ChoiceFilter(choices=CollectionItem.BookFormat.choices)
    purchase_date = filters.DateFilter()
    purchase_date_gt = filters.DateFilter(field_name="purchase_date", lookup_expr="gt")
    purchase_date_lt = filters.DateFilter(field_name="purchase_date", lookup_expr="lt")
    purchase_date_gte = filters.DateFilter(field_name="purchase_date", lookup_expr="gte")
    purchase_date_lte = filters.DateFilter(field_name="purchase_date", lookup_expr="lte")
    purchase_store = filters.CharFilter(lookup_expr="icontains")
    storage_location = filters.CharFilter(lookup_expr="icontains")
    issue__series = filters.NumberFilter(field_name="issue__series__id")
    is_read = filters.BooleanFilter()
    date_read = filters.DateFilter(field_name="date_read__date")  # Uses __date lookup for DateTimeField
    date_read_gt = filters.DateFilter(field_name="date_read__date", lookup_expr="gt")
    date_read_lt = filters.DateFilter(field_name="date_read__date", lookup_expr="lt")
    date_read_gte = filters.DateFilter(field_name="date_read__date", lookup_expr="gte")
    date_read_lte = filters.DateFilter(field_name="date_read__date", lookup_expr="lte")
    grade = filters.ChoiceFilter(choices=GRADE_CHOICES)
    grading_company = filters.ChoiceFilter(choices=CollectionItem.GradingCompany.choices)
    rating = filters.NumberFilter()
    modified_gt = filters.DateTimeFilter(field_name="modified", lookup_expr="gt")
```

**Usage:** REST API filtering via django-filter

**Note:** `date_read` filters use `__date` lookup because `date_read` is a DateTimeField. This allows date-based filtering while preserving precise timestamp data for scrobble functionality.

### CollectionViewFilter (Web UI)

```python
class CollectionViewFilter(df.FilterSet):
    # Quick search across multiple fields
    q = QuickSearchFilter(label="Quick Search")

    # Series filters
    series_name = CollectionSeriesName(field_name="issue__series__name")
    series_type = df.NumberFilter(field_name="issue__series__series_type__id")
    issue_number = df.CharFilter(field_name="issue__number", lookup_expr="iexact")

    # Publisher/Imprint filters
    publisher_name = df.CharFilter(field_name="issue__series__publisher__name", lookup_expr="icontains")
    publisher_id = df.NumberFilter(field_name="issue__series__publisher__id")
    imprint_name = df.CharFilter(field_name="issue__series__imprint__name", lookup_expr="icontains")
    imprint_id = df.NumberFilter(field_name="issue__series__imprint__id")

    # Collection metadata
    book_format = df.ChoiceFilter(choices=CollectionItem.BookFormat.choices)
    is_read = df.BooleanFilter()
    storage_location = df.CharFilter(lookup_expr="icontains")
    purchase_store = df.CharFilter(lookup_expr="icontains")

    # Grading
    grade = df.ChoiceFilter(choices=GRADE_CHOICES)
    grading_company = df.ChoiceFilter(choices=CollectionItem.GradingCompany.choices)

    # Rating
    rating = df.NumberFilter()
```

**Custom Filters:**

```python
class CollectionSeriesName(df.CharFilter):
    """Multi-word series name search (all words must match)."""
    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(operator.and_,
                    (Q(issue__series__name__unaccent__icontains=q) for q in query_list)
                )
            )
        return super().filter(qs, value)

class QuickSearchFilter(df.CharFilter):
    """Search across series names and notes."""
    def filter(self, qs, value):
        if value:
            query_list = value.split()
            return qs.filter(
                reduce(operator.and_,
                    (Q(issue__series__name__unaccent__icontains=q) |
                     Q(notes__icontains=q) for q in query_list)
                )
            )
        return super().filter(qs, value)
```

**Usage:** Web UI filtering with comprehensive options

## HTMX Integration

### Star Rating System

**File:** `user_collection/templates/user_collection/partials/star_rating.html`

The collection uses HTMX for real-time star rating updates without page refresh.

**HTMX Attributes:**

```html
<form hx-post="{% url 'user_collection:rate' item.pk %}"
      hx-target="#rating-{{ item.pk }}"
      hx-swap="outerHTML">
    {% csrf_token %}
    <!-- Star buttons 1-5 -->
    <button type="submit" name="rating" value="1">★</button>
    <button type="submit" name="rating" value="2">★</button>
    <!-- ... -->
</form>
```

**Features:**

- **Real-time updates**: Click a star, rating updates instantly
- **No page refresh**: HTMX swaps only the star rating element
- **Visual feedback**: Active stars highlighted
- **Clearable**: Can remove rating by clicking same star
- **Progressive enhancement**: Falls back to standard form submission

**Flow:**

1. User clicks star (1-5)
2. HTMX sends POST to `/collection/<pk>/rate/`
3. View updates rating in database
4. View returns updated partial template
5. HTMX swaps old rating HTML with new
6. User sees updated stars immediately

**Benefits:**

- Improved UX with instant feedback
- Reduced server load (partial template only)
- Mobile-friendly single-click rating
- Consistent with project's HTMX-first approach

### Range Toggle (Add from Series)

**File:** `user_collection/templates/user_collection/add_issues_from_series.html`

The bulk addition form uses HTMX for showing/hiding range input fields:

```html
<div class="control"
     hx-on:change="
         if (event.target.name === 'range_type') {
             const rangeFields = document.getElementById('range-fields');
             rangeFields.style.display = event.target.value === 'range' ? 'block' : 'none';
         }
     ">
```

**Features:**

- Co-located event handling with UI
- Shows range fields only when "Issue range" selected
- Hides fields when "All issues" selected
- ~50% reduction in JavaScript vs separate file

## Autocomplete

**File:** `comicsdb/autocomplete.py`

### IssueAutocomplete

```python
class IssueAutocomplete(ModelAutocomplete):
    model = Issue
    search_attrs = ["series__name", "number"]
```

Used in `CollectionItemForm` for issue selection.

**Smart Search:**

- Basic: OR search across series name and number
- Smart: AND search when `#` separator used
- Example: `"spider #1"` → series contains "spider" AND number contains "1"

**Queryset Optimization:**

```python
queryset = Issue.objects.select_related("series", "series__series_type")
```

### SeriesAutocomplete

```python
class SeriesAutocomplete(ModelAutocomplete):
    model = Series
    search_attrs = ["name"]
```

Used in `AddIssuesFromSeriesForm` for bulk addition.

**Features:**

- Simple name-based search
- Optimized with `select_related("series_type")`
- Returns formatted results with series type

## Templates

**Directory:** `user_collection/templates/user_collection/`

### Template Files

| Template | Purpose | Key Features |
|----------|---------|--------------|
| `collection_list.html` | List all items | Pagination, filtering, star ratings, stats link |
| `collection_detail.html` | Single item detail | Cover image, all metadata, edit/delete buttons |
| `collection_form.html` | Create/edit form | Autocomplete, date pickers, help text |
| `collection_confirm_delete.html` | Delete confirmation | Item details, warning |
| `collection_stats.html` | Statistics dashboard | Charts, totals, top series |
| `add_issues_from_series.html` | Bulk add from series | Series autocomplete, HTMX range toggle |
| `missing_issues_list.html` | Series with missing issues | Completion percentage, progress bars, pagination |
| `missing_issues_detail.html` | Specific missing issues | Chronological list, issue details, series stats |
| `partials/star_rating.html` | Star rating component | HTMX-enabled, reusable |
| `partials/collection_filter.html` | Filter form | All filter options, clear button |

### Template Context

**Common Context Variables:**

- `item`: CollectionItem instance (detail/update/delete)
- `collection_items`: Queryset of items (list)
- `form`: Form instance (create/update/bulk add)
- `user`: Current user (from request)
- `has_active_filters`: Boolean for showing "Clear Filters" (list)

**Stats Context:**

- `total_items`: Total unique items
- `total_quantity`: Total comics including copies
- `total_value`: Sum of purchase prices
- `read_count`: Read items count
- `unread_count`: Unread items count
- `format_counts`: Breakdown by format
- `top_series`: Top 10 series by count

**Missing Issues Context:**

List View:

- `series_list`: Queryset of Series with annotations (total_issues, owned_issues, missing_count)
- `series_with_missing_count`: Total number of series with missing issues

Detail View:

- `series`: Series object being viewed
- `missing_issues`: Queryset of Issue objects user doesn't own
- `total_issues`: Total issues in the series
- `owned_issues`: Number of issues user owns
- `missing_count`: Number of issues user doesn't own
- `completion_percentage`: Percentage of series owned (rounded to 1 decimal)

### Bulma CSS Framework

Templates use Bulma CSS for styling:

- Form fields wrapped in Bulma control classes
- Buttons use Bulma button styles
- Tables use Bulma table classes
- Messages use Bulma notification styles
- Pagination uses Bulma pagination

## Database Optimization

### QuerySet Optimizations

**List View:**

```python
queryset = (
    CollectionItem.objects.filter(user=request.user)
    .select_related(
        "issue__series__series_type",
        "issue__series__publisher",
        "issue__series__imprint",
    )
    .order_by("issue__series__sort_name", "issue__cover_date")
)
```

**Detail View:**

```python
queryset = CollectionItem.objects.select_related(
    "issue",
    "issue__series",
    "issue__series__publisher",
)
```

**Stats View:**

```python
# Aggregate queries
total_quantity = queryset.aggregate(Sum("quantity"))["quantity__sum"]
total_value = queryset.aggregate(Sum("purchase_price"))["purchase_price__sum"]
format_counts = queryset.values("book_format").annotate(count=Count("id"))
```

**Missing Issues List View:**

```python
queryset = (
    Series.objects.annotate(
        total_issues=Count("issues", distinct=True),
        owned_issues=Count(
            "issues", filter=Q(issues__in_collections__user=user), distinct=True
        ),
    )
    .annotate(missing_count=F("total_issues") - F("owned_issues"))
    .filter(owned_issues__gt=0, missing_count__gt=0)
    .select_related("publisher", "series_type", "imprint")
    .order_by("-missing_count", "sort_name")
)
```

**Missing Issues Detail View:**

```python
# Two-query strategy for efficiency
owned_issue_ids = CollectionItem.objects.filter(
    user=user, issue__series_id=series_id
).values_list("issue_id", flat=True)

missing_issues = (
    Issue.objects.filter(series_id=series_id)
    .exclude(id__in=owned_issue_ids)
    .select_related("series", "series__publisher", "series__series_type")
    .order_by("cover_date", "number")
)
```

**Benefits:**

- `select_related()`: Reduces queries for ForeignKey relationships
- `aggregate()`: Database-level calculations
- `annotate()`: Efficient grouping and counting
- `F()` expressions: Database-level arithmetic
- Conditional `Count()` with filters: Efficient user-scoped counting
- `values_list()` with `flat=True`: Memory-efficient ID lists
- `exclude()` with `id__in`: Set-based exclusion
- Ordered querysets use database sorting

### Indexes

```python
class Meta:
    indexes = [
        models.Index(fields=["user", "issue"], name="user_issue_idx"),
        models.Index(fields=["user", "purchase_date"], name="user_purchase_date_idx"),
        models.Index(fields=["user", "book_format"], name="user_format_idx"),
        models.Index(fields=["user", "is_read"], name="user_is_read_idx"),
        models.Index(fields=["user", "grade"], name="user_grade_idx"),
        models.Index(fields=["user", "grading_company"], name="user_grading_company_idx"),
    ]
```

**Purpose:**

All indexes include `user` as the first field because:
- All queries filter by user (privacy requirement)
- Composite indexes optimize common filter combinations
- Covering indexes reduce index-only scans

**Query Patterns Optimized:**

- `WHERE user=X AND is_read=False` → Uses `user_is_read_idx`
- `WHERE user=X AND grade='9.6'` → Uses `user_grade_idx`
- `WHERE user=X AND book_format='PRINT'` → Uses `user_format_idx`

### Database Constraints

**Unique Constraint:**

```python
unique_together = ["user", "issue"]
```

**Benefits:**

- Prevents duplicate issues in user's collection
- Database-level enforcement (not just app-level)
- Faster lookups on unique pairs
- Data integrity guarantee

**Validation:**

The constraint is checked in the form's `clean_issue()` method before database insertion to provide user-friendly error messages.

## API Integration

### Internal Dependencies

**comicsdb.models.Issue:**

```python
from comicsdb.models.issue import Issue
```

Used for the M2M-like relationship and autocomplete.

**comicsdb.models.Series:**

```python
from comicsdb.models.series import Series
```

Used for bulk addition from series.

**comicsdb.filters:**

```python
from comicsdb.filters.collection import CollectionViewFilter
```

Shared filter classes for consistency between web and API.

**users.models.CustomUser:**

```python
from users.models import CustomUser
```

Used for user ownership and authentication.

### External Dependencies

**autocomplete package:**

```python
from autocomplete import ModelAutocomplete, register, widgets
```

Provides autocomplete functionality for issue and series search.

**django-filter:**

```python
import django_filters as df
from django_filters import rest_framework as filters
```

Advanced filtering for both web UI and API.

**django-money:**

```python
from djmoney.models.fields import MoneyField
```

Currency field for purchase price tracking.

### REST API Endpoints

The collection feature provides read-only REST API endpoints. Complete API documentation is available in the main [API README](../api/README.md#collection).

**Available Endpoints:**

- `GET /api/collection/` - List user's collection items
- `GET /api/collection/{id}/` - Retrieve collection item details
- `GET /api/collection/stats/` - Get collection statistics

**Authentication:**

All collection API endpoints require authentication. Users can only access their own collection items.

**Permissions:**

- Authenticated users can access only their own collection
- No admin special access (unlike reading lists)
- Attempting to access another user's item returns 404

For complete API documentation including filtering, pagination, and response formats, see the [main API documentation](../api/README.md#collection).

## Privacy and Security

### Privacy Model

**Strictly Private:**

- Collections are always private (no public/private toggle)
- Users can only see their own collection items
- No sharing or collaboration features
- API access restricted to owner

### Permission Checks

**View-Level:**

All views use `LoginRequiredMixin` for authentication.

Views that access specific items use `UserPassesTestMixin`:

```python
def test_func(self):
    item = self.get_object()
    return item.user == self.request.user
```

**Queryset-Level:**

All querysets are filtered by user:

```python
queryset = CollectionItem.objects.filter(user=self.request.user)
```

**Form-Level:**

Forms validate duplicate issues only within user's collection:

```python
CollectionItem.objects.filter(user=self.user, issue=issue).exists()
```

### Security Considerations

**CSRF Protection:**

All forms include `{% csrf_token %}` for CSRF protection.

**SQL Injection:**

Django ORM prevents SQL injection via parameterized queries.

**XSS Prevention:**

Django templates auto-escape output by default.

**Access Control:**

- User ID from `request.user` (authenticated session)
- Never trust user input for user ID
- Permission checks on every view
- Queryset scoping prevents data leakage

## Testing

### Test Coverage Areas

**Models:**

- CollectionItem creation and validation
- Unique constraint enforcement (user, issue)
- Choice field validation (BookFormat, GradingCompany, Grade)
- MoneyField handling
- Rating range validation (1-5)

**Views:**

- Authentication requirements (LoginRequiredMixin)
- Permission checks (owner-only access)
- Queryset filtering (user-scoped)
- Form validation
- Success/error messages
- Redirection flows

**Forms:**

- CollectionItemForm validation
- Duplicate issue prevention
- User context passing
- AddIssuesFromSeriesForm range validation
- Field widget configuration

**Filters:**

- CollectionFilter field coverage
- CollectionViewFilter custom filters
- QuickSearchFilter multi-field search
- Series name multi-word search
- Date range filtering

**HTMX:**

- Star rating endpoint
- Partial template rendering
- Owner-only rating updates
- Rating value validation (1-5)
- Clear rating functionality (value=0)

**Bulk Addition:**

- Add all issues from series
- Range filtering (start/end/both)
- Duplicate detection
- Default format application
- Mark as read functionality
- bulk_create() operations
- Success/skip messaging

**Missing Issues:**

- MissingIssuesListView queryset filtering
- MissingIssuesDetailView queryset exclusion
- Series annotation calculations (total_issues, owned_issues, missing_count)
- Completion percentage calculations
- Permission checks (user-scoped)
- Pagination handling

**Scrobble Endpoint:**

- Request validation (ScrobbleRequestSerializer)
- Issue existence validation
- Rating range validation (1-5)
- Auto-creation of collection items
- Auto-update of existing items
- Default value assignment (quantity=1, book_format=DIGITAL)
- Timestamp handling (timezone.now() default)
- Response serialization with created flag
- Status code differentiation (201 vs 200)
- User-scoped permissions
- Error handling (404 for missing issues)

### Test Fixtures

**Recommended Fixtures:**

- `user`: Standard user for ownership
- `other_user`: Different user for permission testing
- `issue`: Basic issue for collection
- `series_with_issues`: Series with multiple sequential issues
- `collection_item`: Pre-populated collection item
- `collection_with_items`: User with multiple collection items

### Example Tests

**Model Tests:**

```python
class CollectionItemModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="testuser")
        self.issue = Issue.objects.create(...)

    def test_unique_constraint(self):
        """Test that users cannot add the same issue twice."""
        CollectionItem.objects.create(user=self.user, issue=self.issue)

        with self.assertRaises(IntegrityError):
            CollectionItem.objects.create(user=self.user, issue=self.issue)

    def test_different_users_can_own_same_issue(self):
        """Test that different users can collect the same issue."""
        other_user = CustomUser.objects.create_user(username="other")

        item1 = CollectionItem.objects.create(user=self.user, issue=self.issue)
        item2 = CollectionItem.objects.create(user=other_user, issue=self.issue)

        self.assertIsNotNone(item1.pk)
        self.assertIsNotNone(item2.pk)
        self.assertNotEqual(item1.pk, item2.pk)
```

**Missing Issues View Tests:**

```python
class MissingIssuesViewTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(username="testuser")
        self.client.force_login(self.user)

        # Create a series with 5 issues
        self.series = Series.objects.create(name="Test Series")
        self.issues = [
            Issue.objects.create(series=self.series, number=str(i))
            for i in range(1, 6)
        ]

        # User owns issues 1, 2, and 4
        for issue_num in [0, 1, 3]:
            CollectionItem.objects.create(
                user=self.user,
                issue=self.issues[issue_num]
            )

    def test_missing_issues_list_shows_incomplete_series(self):
        """Test that series with missing issues appears in the list."""
        response = self.client.get(reverse("user_collection:missing-list"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(self.series, response.context["series_list"])

        # Check annotations
        series = response.context["series_list"].get(pk=self.series.pk)
        self.assertEqual(series.total_issues, 5)
        self.assertEqual(series.owned_issues, 3)
        self.assertEqual(series.missing_count, 2)

    def test_missing_issues_detail_shows_correct_issues(self):
        """Test that detail view shows only missing issues."""
        response = self.client.get(
            reverse("user_collection:missing-detail", args=[self.series.id])
        )

        self.assertEqual(response.status_code, 200)
        missing = response.context["missing_issues"]

        # Should show issues 3 and 5 (indices 2 and 4)
        self.assertEqual(missing.count(), 2)
        self.assertIn(self.issues[2], missing)
        self.assertIn(self.issues[4], missing)

        # Should NOT show owned issues
        self.assertNotIn(self.issues[0], missing)
        self.assertNotIn(self.issues[1], missing)
        self.assertNotIn(self.issues[3], missing)

    def test_completion_percentage_calculation(self):
        """Test that completion percentage is calculated correctly."""
        response = self.client.get(
            reverse("user_collection:missing-detail", args=[self.series.id])
        )

        # 3 out of 5 = 60%
        self.assertEqual(response.context["completion_percentage"], 60.0)
```

## Future Enhancements

### Recently Implemented

**Missing Issues Functionality** ✓

- Identify series where user owns some but not all issues
- View specific missing issues for each series
- Track completion percentage by series
- Color-coded progress indicators (red/yellow/green)
- Prioritize series by missing issue count
- Generate shopping lists for completing runs

See [MissingIssuesListView](#missingissueslistview) and [MissingIssuesDetailView](#missingissuesdetailview) for technical details.

**Scrobble API Endpoint** ✓

- Quick scrobble endpoint for marking issues as read via API
- Auto-creates collection items if issue not already owned
- Auto-updates existing collection items with read status
- Precise timestamp tracking with DateTimeField
- Optional rating support (1-5 stars)
- Defaults to timezone.now() for date_read if not provided
- Returns 201 for new items, 200 for updates
- Mobile app and browser extension ready

**Database Migration:** `date_read` field changed from DateField to DateTimeField for precise scrobble tracking (migration `0002_collectionitem_date_read_datetime.py`).

See [scrobble](#scrobble-api-viewset-action) for technical details.

### Planned Features

1. **Wishlist Functionality**
    - Separate wishlist for issues to acquire
    - Price tracking for wishlist items
    - Notifications for price drops
    - Convert wishlist items to collection

2. **Enhanced Statistics**
    - Value appreciation tracking
    - Most valuable issues
    - Reading velocity (issues per month)
    - Grade distribution charts
    - Publisher/imprint breakdowns
    - ~~Completion percentage by series~~ ✓ Implemented (see Missing Issues feature)

3. **Import/Export**
    - CSV import for bulk collection entry
    - Export to various formats (CSV, JSON, PDF)
    - Comic collector software integration
    - Backup and restore functionality

4. **Reading Progress**
    - Reading list integration
    - Mark issues from reading lists as read in collection
    - Track reading order vs collection order
    - Reading statistics and history

5. **Variant Tracking**
    - Support for multiple variants of same issue
    - Variant type field (cover, incentive, etc.)
    - Artist/variant name tracking
    - Display variants grouped by base issue

6. **Collection Sharing** (Optional)
    - Public profile option
    - Share collection statistics
    - Public wishlist for trades
    - Privacy controls (what to share)

7. **Mobile App**
    - Native iOS/Android apps
    - Barcode scanning for quick addition
    - Offline access to collection
    - Photo uploads for condition documentation

### Possible Technical Improvements

1. **Caching**
    - Redis cache for statistics
    - Cache frequently accessed collections
    - Template fragment caching for lists
    - Cache invalidation on updates

2. **Async Operations**
    - Celery tasks for bulk operations
    - Background import/export jobs
    - Email notifications for completed tasks
    - Progress tracking for long operations

3. **Search Enhancements**
    - Full-text search with PostgreSQL
    - Elasticsearch integration for large collections
    - Advanced search with boolean operators
    - Saved search filters

4. **Performance**
    - Denormalize series count
    - Materialized views for statistics
    - Query result pagination improvements
    - Database sharding for large user base

5. **Data Visualization**
    - Chart.js integration for statistics
    - Timeline view of purchases
    - Grade distribution histogram
    - Collection value over time graph

6. **Integration APIs**
    - CLZ Comics integration
    - Comic Book Realm integration
    - League of Comic Geeks sync
    - Goodreads-style social features

---

For user documentation and usage instructions, see [README.md](README.md).
