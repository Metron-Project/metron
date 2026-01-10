# User Collection - User Guide

The User Collection feature allows you to catalog, organize, and track your personal comic book collection. Keep detailed records of what you own, including condition grades, purchase information, reading status, and personal ratings.

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
- [Usage Examples](#usage-examples)
- [Grading System](#grading-system)
- [Filtering and Search](#filtering-and-search)
- [Collection Statistics](#collection-statistics)
- [URLs Quick Reference](#urls-quick-reference)
- [Tips and Best Practices](#tips-and-best-practices)

## Features

### Core Functionality

- **Catalog Your Comics**: Track every issue in your collection
- **Bulk Addition**: Add entire series runs quickly
- **Grading Support**: Record professional grades (CGC, CBCS, PGX) or your own assessments
- **Reading Tracker**: Mark issues as read and track when you read them
- **Star Ratings**: Rate your comics from 1 to 5 stars
- **Purchase Tracking**: Record when, where, and how much you paid
- **Storage Management**: Track where your comics are stored
- **Format Tracking**: Distinguish between print, digital, and both

### Detailed Tracking

Your collection records can include:

- **Ownership Details**: Quantity, format (print/digital/both)
- **Condition**: Grade on CGC scale (0.5 to 10.0) and grading company
- **Purchase Information**: Date, price, and store
- **Storage**: Physical location for easy retrieval
- **Reading Status**: Track multiple read dates for re-reads
- **Personal Rating**: 1-5 star rating system
- **Notes**: Custom notes for each item

### Advanced Features

- **Smart Filtering**: Filter by series, publisher, grade, format, read status, and more
- **Statistics Dashboard**: Track your collection's size, value, and reading progress
- **Gap Identification**: Discover which issues are missing from your series runs
- **Duplicate Detection**: Prevents adding the same issue twice
- **Quick Scrobble**: Instantly mark issues as read via API with optional rating
- **Privacy**: Your collection is completely private to you

## Getting Started

### Viewing Your Collection

**Browse Your Collection**

- Visit `/collection/` to see all your collection items
- Items are sorted by series name and cover date
- Requires login (collections are private)

**View Statistics**

- Visit `/collection/stats/` to see:
    - Total items and quantity
    - Total collection value
    - Read vs unread counts
    - Format breakdown (print/digital)
    - Top 10 series in your collection

### Adding Your First Comic

1. Log in to your account
2. Navigate to `/collection/add/`
3. Search for and select the issue
4. Enter details:
    - Quantity (default: 1)
    - Format (print/digital/both)
    - Grade and grading company (optional)
    - Purchase information (optional)
    - Storage location (optional)
5. Click "Add to Collection"

## Usage Examples

### Adding Individual Issues

1. Navigate to `/collection/add/`
2. Search for the issue using autocomplete
3. Fill in optional details:
    - **Quantity**: How many copies you own
    - **Format**: Print, Digital, or Both
    - **Grade**: Select from CGC scale (e.g., 9.6)
    - **Grading Company**: CGC, CBCS, or PGX (leave blank for your own assessment)
    - **Purchase Date**: When you acquired it
    - **Purchase Price**: How much you paid
    - **Purchase Store**: Where you bought it
    - **Storage Location**: Where it's stored (e.g., "Longbox 1", "Shelf A")
    - **Notes**: Any additional information
4. Click "Add to Collection"

**Tips:**

- You can only add each issue once (use quantity field for multiple copies)
- Grading company is optional - leave blank if you're assessing the grade yourself
- All fields except the issue itself are optional

### Adding Multiple Issues from a Series

Perfect for quickly adding entire series runs to your collection!

1. Navigate to `/collection/add-from-series/`
2. Search for and select a series
3. Choose what to add:
    - **All issues**: Adds every issue from the series
    - **Issue range**: Specify start and/or end issue numbers
        - Example: Start at #1, end at #50 (adds issues 1-50)
        - Example: Start at #10 (adds issue 10 through the end)
        - Example: End at #25 (adds beginning through issue 25)
4. Set default options:
    - **Default Format**: Print, Digital, or Both (applied to all issues)
    - **Mark as Read**: Optionally mark all issues as read
5. Click "Add Issues"

**Benefits:**

- Add hundreds of issues in seconds
- Perfect for cataloging longboxes or digital libraries
- Automatically skips issues already in your collection
- You can update details for individual issues later

**Example Workflow:**

1. Add Amazing Spider-Man Vol 1, all issues, format: Print
2. Add X-Men Vol 1, issues #1-50, format: Print
3. Update individual issues with grades, purchase info, etc.

### Viewing Collection Items

**List View** (`/collection/`)

- Shows all your collection items
- Displays: Series, issue number, format, grade, read status, rating
- Paginated (50 items per page)
- Use filters to narrow down results

**Detail View** (`/collection/<id>/`)

- Full details for a single collection item
- Shows cover image and description
- Displays all tracking information
- Access to Edit and Delete buttons

### Tracking Read Dates

Comics are commonly re-read, so the collection tracks multiple read dates per item.

**Managing Read Dates (Detail Page):**

1. Navigate to the item's detail page
2. View all your read dates in chronological order
3. Add a new read date:
   - Click "Add Read Date"
   - Select the date and time (defaults to now)
   - Click "Add" to save
4. Delete a read date:
   - Click the "Delete" button next to any read date
   - The item automatically marks as unread if you delete all read dates

**How It Works:**

- Each time you read an issue, add a new read date
- All read dates are preserved in your history
- The most recent read date is displayed prominently
- The `is_read` status automatically syncs:
  - `True` when you have at least one read date
  - `False` when you have no read dates
- Scrobbling via API adds a new read date instead of replacing

**Example:**

- First read: January 5, 2026
- Re-read: March 15, 2026
- Third read: June 20, 2026

All three dates are tracked separately, allowing you to see your complete reading history for each issue.

### Editing a Collection Item

1. Navigate to the item's detail page
2. Click "Edit" or "Update"
3. Modify any fields
4. Click "Update" to save changes

**What You Can Edit:**

- Quantity
- Format
- Grade and grading company
- Purchase information
- Storage location
- Notes
- Rating

**Note:** You cannot change which issue the collection item refers to. If you need to track a different issue, delete this item and create a new one. Read dates are managed separately on the detail page, not in the edit form.

### Rating Your Comics

You can rate comics on a 1-5 star scale:

**Method 1: Quick Rating (List View)**

- On the collection list page, click the stars next to any item
- Rating updates instantly via HTMX

**Method 2: Edit Form**

- Edit the collection item
- Select a rating (1-5 stars)
- Save the form

**Ratings Help You:**

- Remember which comics you loved
- Filter your collection by rating
- Track your favorites

### Removing Issues from Your Collection

1. Navigate to the item's detail page
2. Click "Delete"
3. Confirm the deletion
4. The item is permanently removed from your collection

**Note:** This only removes the item from your collection - it does not delete the issue from the Metron database.

### Finding Missing Issues in Your Series

Identify gaps in your series runs to help complete your collection!

**Missing Issues List** (`/collection/missing/`)

1. From your collection, click "Missing Issues" button
2. View all series where you own some but not all issues
3. See at a glance:
    - **Completion Progress**: Color-coded progress bars
        - Red: Less than 50% complete
        - Yellow: 50-80% complete
        - Green: More than 80% complete
    - **Statistics**: "You own X of Y issues (Z% complete)"
    - **Missing Count**: Number of issues you don't have
4. Click "View Missing" to see specific issues

**Missing Issues Detail** (`/collection/missing/<series_id>/`)

1. Shows the specific series information
2. Lists all missing issues in chronological order
3. For each missing issue, see:
    - Issue number and cover date
    - Issue title/description
4. Use this list to plan purchases or fill gaps

**Benefits:**

- Quickly identify incomplete series runs
- Prioritize which issues to acquire next
- Track your progress toward completing series
- Focus collecting efforts on series you've already started
- Only shows issues that exist in the Metron database

**Example Workflow:**

1. Click "Missing Issues" from your collection
2. See Amazing Spider-Man Vol 1 at 45% complete
3. Click "View Missing" to see issues #23, #45, #67, etc.
4. Use this list when shopping for back issues
5. After purchasing, add the issues to your collection
6. Return to Missing Issues to track updated progress

**Note:** Missing Issues only shows series where you own at least one issue. It helps you complete runs you've already started, not discover new series.

### Quick Scrobble (API)

The scrobble feature allows you to quickly mark issues as read via the API, perfect for mobile apps or browser extensions.

**Endpoint:** `POST /api/collection/scrobble/`

**Purpose:**

- Instantly mark an issue as read without navigating through the web UI
- Automatically creates a collection item if the issue isn't already in your collection
- Adds a new read date to existing items (preserves all previous read dates)

**Request Body:**

```json
{
  "issue_id": 12345,
  "date_read": "2026-01-08T14:30:00Z",  // Optional, defaults to now
  "rating": 4                             // Optional, 1-5 stars
}
```

**Response (201 Created - New Item):**

```json
{
  "id": 789,
  "issue": {
    "id": 12345,
    "series_name": "Amazing Spider-Man",
    "number": "300"
  },
  "is_read": true,
  "date_read": "2026-01-08T14:30:00Z",
  "read_dates": [
    "2026-01-08T14:30:00Z"
  ],
  "read_count": 1,
  "rating": 4,
  "created": true,
  "modified": "2026-01-08T14:30:00Z"
}
```

**Response (200 OK - Updated Existing):**

```json
{
  "id": 456,
  "issue": {
    "id": 12345,
    "series_name": "Amazing Spider-Man",
    "number": "300"
  },
  "is_read": true,
  "date_read": "2026-01-08T14:30:00Z",
  "read_dates": [
    "2026-01-08T14:30:00Z",
    "2025-12-15T10:00:00Z",
    "2025-11-01T08:30:00Z"
  ],
  "read_count": 3,
  "rating": 4,
  "created": false,
  "modified": "2026-01-08T14:30:00Z"
}
```

**Auto-Creation Behavior:**

When scrobbling an issue not in your collection, a new collection item is automatically created with:

- `quantity`: 1
- `book_format`: DIGITAL
- `is_read`: true
- `date_read`: From request or current timestamp
- `read_dates`: Array with single entry
- `rating`: From request (if provided)

**Read Date Behavior:**

- Scrobbling ADDS a new read date (doesn't replace existing ones)
- All previous read dates are preserved
- The `date_read` field shows the most recent read
- The `read_count` field shows total number of reads
- Perfect for tracking re-reads over time

**Use Cases:**

1. **Reading Tracker App**: Mark issues as read immediately after finishing them
2. **Browser Extension**: One-click scrobble while reading digital comics
3. **Import Tool**: Bulk import reading history from other services
4. **Mobile App**: Quick scrobble without full collection interface
5. **Re-read Tracking**: Scrobble the same issue multiple times to track re-reads

**Example with curl:**

```bash
# Mark issue #12345 as read right now
curl -X POST https://metron.cloud/api/collection/scrobble/ \
  -u "username:password" \
  -H "Content-Type: application/json" \
  -d '{"issue_id": 12345}'

# Mark as read with specific date and rating
curl -X POST https://metron.cloud/api/collection/scrobble/ \
  -u "username:password" \
  -H "Content-Type: application/json" \
  -d '{
    "issue_id": 12345,
    "date_read": "2026-01-08T10:00:00Z",
    "rating": 5
  }'
```

**Benefits:**

- **Fast**: One API call to mark as read
- **Automatic**: Creates collection items automatically
- **Precise**: Tracks exact read timestamp (not just date)
- **Flexible**: Works with existing or new collection items
- **Re-read Friendly**: Adds to history instead of replacing
- **Private**: Respects collection privacy (user-scoped)

## Grading System

### CGC Grading Scale

The collection uses the standard 10-point CGC (Certified Guaranty Company) grading scale:

**Mint to Near Mint (9.0-10.0)**

- `10.0` - Gem Mint
- `9.9` - Mint
- `9.8` - NM/M (Near Mint/Mint)
- `9.6` - NM+ (Near Mint+)
- `9.4` - NM (Near Mint)
- `9.2` - NM- (Near Mint-)
- `9.0` - VF/NM (Very Fine/Near Mint)

**Very Fine (7.5-8.5)**

- `8.5` - VF+ (Very Fine+)
- `8.0` - VF (Very Fine)
- `7.5` - VF- (Very Fine-)

**Fine (5.5-7.0)**

- `7.0` - FN/VF (Fine/Very Fine)
- `6.5` - FN+ (Fine+)
- `6.0` - FN (Fine)
- `5.5` - FN- (Fine-)

**Very Good to Good (1.8-5.0)**

- `5.0` - VG/FN (Very Good/Fine)
- `4.5` - VG+ (Very Good+)
- `4.0` - VG (Very Good)
- `3.5` - VG- (Very Good-)
- `3.0` - GD/VG (Good/Very Good)
- `2.5` - GD+ (Good+)
- `2.0` - GD (Good)
- `1.8` - GD- (Good-)

**Fair to Poor (0.5-1.5)**

- `1.5` - FR/GD (Fair/Good)
- `1.0` - FR (Fair)
- `0.5` - PR (Poor)

### Grading Companies

The collection supports three major grading companies:

- **CGC** - CGC (Certified Guaranty Company)
    - Most widely recognized grading service
    - Blue label for unrestored comics

- **CBCS** - CBCS (Comic Book Certification Service)
    - Second largest grading company
    - Known for verified signatures

- **PGX** - PGX (Professional Grading Experts)
    - Alternative grading service
    - Often more affordable

**User-Assessed Grades:**

Leave the grading company field blank if you're assessing the grade yourself. This is common for:

- Ungraded comics in your collection
- Personal reference before professional grading
- Comics you don't plan to professionally grade

## Filtering and Search

### Available Filters

The collection list view supports extensive filtering:

**Series Filters:**

- **Series Name**: Search for series (case-insensitive, searches all words)
- **Series Type**: Filter by series type (ongoing, mini-series, etc.)
- **Issue Number**: Find specific issue numbers across all series

**Publisher/Imprint:**

- **Publisher Name**: Filter by publisher
- **Publisher ID**: Exact publisher match
- **Imprint Name**: Filter by imprint
- **Imprint ID**: Exact imprint match

**Collection Metadata:**

- **Format**: Print, Digital, or Both
- **Storage Location**: Search your storage locations
- **Purchase Store**: Find items from specific stores

**Condition:**

- **Grade**: Filter by specific grade (e.g., 9.6)
- **Grading Company**: CGC, CBCS, or PGX

**Reading Status:**

- **Is Read**: Show only read or unread comics
- **Rating**: Filter by star rating (1-5)

**Quick Search:**

- Search across series names and your notes simultaneously

### Filter Examples

```
# Find all unread comics
?is_read=false

# Find all CGC graded 9.8 comics
?grade=9.8&grading_company=CGC

# Find all 5-star rated comics
?rating=5

# Find Amazing Spider-Man issues
?series_name=amazing spider-man

# Find print comics in a specific longbox
?book_format=PRINT&storage_location=longbox 1

# Find all Marvel comics
?publisher_name=marvel

# Combine multiple filters
?series_name=x-men&grade=9.6&is_read=true&rating=5
```

### Filtering Tips

1. **Combine filters**: Use multiple filters together for precise results
2. **Case-insensitive**: All text searches ignore case
3. **Partial matches**: Series and publisher names support partial matching
4. **Clear filters**: Click "Clear Filters" to reset all filters
5. **URL parameters**: Filters persist in the URL for bookmarking

## Collection Statistics

### Statistics Dashboard

Visit `/collection/stats/` to see detailed analytics about your collection:

**Overview Stats:**

- **Total Items**: Number of unique collection entries
- **Total Quantity**: Total comics including duplicates
- **Total Value**: Sum of all purchase prices
- **Read Count**: Number of items you've read
- **Unread Count**: Number of items not yet read

**Format Breakdown:**

- Count by format (Print, Digital, Both)
- Visual breakdown of your collection composition

**Top Series:**

- Top 10 series in your collection by item count
- Helps identify your collecting focus areas

### Using Statistics

**Track Your Investment:**

- Monitor total collection value over time
- See what you've spent on comics

**Reading Progress:**

- Track how much of your collection you've read
- Identify unread comics to prioritize

**Collection Composition:**

- Understand print vs digital balance
- See which series dominate your collection

**Planning:**

- Use top series list to identify gaps in runs
- Plan future purchases based on existing collection

## URLs Quick Reference

| URL | Purpose | Login Required |
|-----|---------|----------------|
| `/collection/` | Browse your collection | Yes |
| `/collection/add/` | Add single issue | Yes |
| `/collection/add-from-series/` | Add issues from series (bulk) | Yes |
| `/collection/stats/` | View collection statistics | Yes |
| `/collection/missing/` | View series with missing issues | Yes |
| `/collection/missing/<series_id>/` | View specific missing issues for a series | Yes |
| `/collection/<id>/` | View item details | Yes* |
| `/collection/<id>/update/` | Edit collection item | Yes* |
| `/collection/<id>/delete/` | Delete collection item | Yes* |
| `/collection/<id>/rate/` | Rate item (HTMX endpoint) | Yes* |
| `/collection/<id>/add-read-date/` | Add read date (HTMX endpoint) | Yes* |
| `/collection/<id>/delete-read-date/<read_date_id>/` | Delete read date (HTMX endpoint) | Yes* |
| `/api/collection/scrobble/` | Mark issue as read (API endpoint) | Yes |

*Must be the owner of the collection item.

## Tips and Best Practices

### Getting Started with Your Collection

1. **Start with key issues**: Add your most valuable or favorite comics first
2. **Use bulk add**: For series runs, use "Add from Series" to save time
3. **Add details incrementally**: You can always come back and add grades, prices, etc.
4. **Use storage locations**: Consistent naming helps you find comics later

### Organizing Your Collection

1. **Storage Location Naming**:
    - Use consistent formats: "Longbox 1", "Longbox 2", "Shelf A", etc.
    - Include location details: "Bedroom Closet - Box 1"
    - For digital: "Comixology", "Marvel Unlimited", etc.

2. **Grading Strategy**:
    - Grade valuable comics first
    - Use consistent standards for self-assessment
    - Note grading company for professionally graded books

3. **Reading Tracking**:
    - Mark issues as read to track progress
    - Use ratings to remember which you enjoyed
    - Add notes for issues you want to revisit

### Managing Large Collections

1. **Bulk Addition**: Use "Add from Series" for runs of 10+ issues
2. **Filter Often**: Use filters to work with subsets of your collection
3. **Update in Batches**: Add issues first, then come back to add grades/prices
4. **Use Notes**: Add searchable notes for special issues or variants

### Tracking Value

1. **Record Purchase Prices**: Track what you paid for investment tracking
2. **Update Regularly**: Revisit valuable issues to update grades if slabbed
3. **Use Statistics**: Monitor total value over time
4. **Note Variants**: Use notes field to distinguish variants and printings

### Privacy and Security

- **Collections are Private**: Only you can see your collection
- **No Public Sharing**: Unlike reading lists, collections cannot be made public
- **API Access**: Read-only API access available at `/api/collection/`

### Completing Series Runs

1. **Check Missing Issues Regularly**: Visit `/collection/missing/` to see your incomplete series
2. **Prioritize High-Completion Series**: Focus on series you're close to completing (80%+)
3. **Use Missing Lists for Shopping**: Check missing issues before visiting comic shops or online stores
4. **Track Progress**: Revisit after adding new issues to see updated completion percentages
5. **Focus Your Collecting**: Use the list to decide which series are worth completing vs starting fresh

### Maintenance Tips

1. **Regular Updates**: Periodically review and update collection details
2. **Remove Sold Items**: Delete items when you sell or give away comics
3. **Mark as Read**: Update reading status to track progress
4. **Review Statistics**: Check stats page to identify collection gaps
5. **Use Missing Issues**: Regularly check `/collection/missing/` to plan purchases

### Common Workflows

**Adding a New Purchase:**

1. Add the issue to your collection
2. Enter purchase date, price, and store
3. Record grade and storage location
4. Leave "is_read" unchecked until you read it

**Cataloging a Longbox:**

1. Identify the series in the longbox
2. Use "Add from Series" for each complete run
3. Add individual issues for incomplete runs
4. Set storage location to "Longbox [number]"
5. Update grades for key issues

**Tracking Reading Progress:**

1. Filter for unread comics (`?is_read=false`)
2. Pick an issue to read
3. After reading, mark as read and add rating
4. Add notes if you want to remember thoughts

**Investment Tracking:**

1. Record purchase prices for all comics
2. Add professional grades for slabbed books
3. Use notes to track appreciation or market changes
4. Review statistics regularly to see total value

**Completing Series Runs:**

1. Visit `/collection/missing/` to see incomplete series
2. Sort by completion percentage to find nearly-complete runs
3. Click "View Missing" on a series you want to complete
4. Note the specific issue numbers and cover dates
5. Search for these issues at comic shops or online
6. Add new acquisitions to your collection
7. Return to Missing Issues to see updated progress

---

For API documentation and developer information, see the main [API README](../api/README.md#collection).
