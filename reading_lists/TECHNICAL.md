# Reading Lists - Technical Documentation

Developer documentation for the `reading_lists` Django app.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Models](#models)
- [Views and URLs](#views-and-urls)
- [Forms](#forms)
- [Permissions](#permissions)
- [Autocomplete](#autocomplete)
- [Templates](#templates)
- [Database Optimization](#database-optimization)
- [API Integration](#api-integration)
- [Testing](#testing)
- [Future Enhancements](#future-enhancements)

## Architecture Overview

The reading_lists app follows Django's MTV (Model-Template-View) pattern with:

- **Models**: `ReadingList` and `ReadingListItem` (through model)
- **Views**: Class-based views (CBVs) for all operations
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
- `reading_list_items`: Prefetched and ordered by `order` field
- `is_owner`: Boolean indicating if user can edit (owner or admin managing Metron)

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

#### RemoveIssueFromReadingListView
```python
class RemoveIssueFromReadingListView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = ReadingListItem
    template_name = "reading_lists/remove_issue_confirm.html"
```

**URL:** `/reading-lists/<slug>/remove-issue/<item_pk>/`

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
    path("<slug:slug>/remove-issue/<int:item_pk>/", RemoveIssueFromReadingListView.as_view(), name="remove-issue"),
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

## Permissions

### Permission Strategy

The app uses `UserPassesTestMixin` for permission checks rather than object-level permissions.

**Base Permission Check:**
```python
def test_func(self):
    reading_list = self.get_object()
    is_owner = reading_list.user == self.request.user
    is_admin_managing_metron = (
        self.request.user.is_staff and
        reading_list.user.username == "Metron"
    )
    return is_owner or is_admin_managing_metron
```

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

**File:** `reading_lists/autocomplete.py`

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

## Templates

**Directory:** `reading_lists/templates/reading_lists/`

### Template Files

| Template | Purpose | Key Features |
|----------|---------|--------------|
| `readinglist_list.html` | List all public lists | Pagination, search link, issue counts |
| `user_readinglist_list.html` | User's own lists | Create button, edit/delete links |
| `readinglist_detail.html` | Single list detail | Ordered issues, add/remove controls |
| `readinglist_form.html` | Create/edit form | Dynamic field visibility |
| `readinglist_confirm_delete.html` | Delete confirmation | Issue count warning |
| `add_issue_autocomplete.html` | Add issues interface | Autocomplete, drag-drop, preview |
| `remove_issue_confirm.html` | Remove issue confirmation | Issue details |

### Template Context

**Common Context Variables:**
- `reading_list`: ReadingList instance
- `reading_list_items`: Ordered queryset of ReadingListItem
- `is_owner`: Boolean for edit permissions
- `user`: Current user (from request)

## Database Optimization

### QuerySet Optimizations

**List Views:**
```python
queryset = ReadingList.objects.select_related("user").annotate(issue_count=Count("issues"))
```

**Detail View:**
```python
queryset = ReadingList.objects.select_related("user").prefetch_related(
    "reading_list_items__issue__series__series_type"
)
```

**Benefits:**
- `select_related()`: Reduces queries for ForeignKey relationships
- `prefetch_related()`: Optimizes M2M and reverse ForeignKey queries
- `annotate()`: Computes issue counts in database

### Indexes

```python
class Meta:
    indexes = [
        models.Index(fields=["reading_list", "order"], name="reading_list_order_idx"),
    ]
```

**Composite Index:**
Optimizes ordering queries on `(reading_list, order)`.

**Standard Indexes:**
- ForeignKey fields auto-indexed
- Unique constraints create indexes
- Slug field indexed via CommonInfo

### Database Constraints

**Unique Constraints:**
- `ReadingList`: `(user, name)`
- `ReadingListItem`: `(reading_list, issue)`

**Benefits:**
- Prevents duplicate data at database level
- Faster lookups on constrained fields
- Data integrity enforcement

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
Provides autocomplete functionality for issue search.

## Testing

### Test File

**File:** `reading_lists/tests.py`

### Recommended Test Coverage

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

**Autocomplete Tests:**
- Basic search
- Smart search with `#`
- Empty queries
- Special characters

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

### Planned Features

1. **List Collaboration**
   - Share lists with specific users
   - Collaborative editing permissions
   - Fork/clone existing lists

3. **Progress Tracking**
   - Mark issues as read/unread
   - Reading progress percentage
   - Completion dates

4. **Enhanced Statistics**
   - Estimated reading time
   - Publisher breakdowns
   - Year distribution charts

5. **Bulk Operations**
   - Add all issues from a series
   - Import from text list
   - Merge multiple lists

6. **API Endpoints**
   - REST API for reading lists
   - JSON export/import
   - Mobile app integration

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

