# Metron API Documentation

Welcome to the Metron API documentation. This API provides programmatic access to comic book metadata including series, issues, characters, creators, and more.

## Table of Contents

- [Overview](#overview)
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Common Patterns](#common-patterns)
- [Endpoints](#endpoints)
    - [Arc](#arc)
    - [Character](#character)
    - [Creator](#creator)
    - [Issue](#issue)
    - [Publisher](#publisher)
    - [Imprint](#imprint)
    - [Series](#series)
    - [Team](#team)
    - [Universe](#universe)
    - [Reading List](#reading-list)
    - [Supporting Resources](#supporting-resources)
- [Filtering](#filtering)
- [Pagination](#pagination)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Additional Resources](#additional-resources)

## Overview

The Metron API is a RESTful API that provides access to a comprehensive database of comic book information. The API supports read operations for all authenticated users and write operations for users in the editor group or administrators.

**Key Features:**

- Comprehensive comic book metadata
- Read and write operations
- Advanced filtering and search
- Paginated responses
- External ID mapping (Comic Vine, Grand Comics Database)
- Image uploads for editor and admin users
- Perceptual hash matching for covers

**Version:** v1.0

## Getting Started

### Quick Start

1. **Explore the API:** Browse available endpoints at `/docs/` (Swagger UI)
2. **Get API Schema:** Download the OpenAPI schema at `/api/schema/`
3. **Authenticate:** Obtain credentials or use session authentication
4. **Make Requests:** Start querying the API endpoints

### Example Request

```bash
# Get a list of issues
curl -X GET https://metron.cloud/api/issue/ \
  -u "username:password"
```

## Authentication

All API endpoints require authentication.

### Authentication Methods

**1. Basic Authentication**

- Use your username and password
- Include in request header: `Authorization: Basic <base64-encoded-credentials>`
- Or use `-u username:password` with curl
- Suitable for programmatic access

### Permissions

- **Authenticated Users:** Full read access to all data
- **Editor Group Members:** Read access plus ability to create and modify content
- **Admin Users:** Full administrative capabilities including all editor permissions

## Base URL

```
https://metron.cloud/api/
```

All endpoints are relative to this base URL.

## Common Patterns

### List and Retrieve

Most resources follow a standard pattern:

- **List:** `GET /api/{resource}/` - Get paginated list
- **Retrieve:** `GET /api/{resource}/{id}/` - Get single item
- **Create:** `POST /api/{resource}/` - Create new item (requires editor or admin)
- **Update:** `PUT/PATCH /api/{resource}/{id}/` - Update item (requires editor or admin)

### Nested Resources

Some resources include nested actions:

- **Issue List:** `GET /api/arc/{id}/issue_list/` - Get issues for a story arc
- **Series List:** `GET /api/publisher/{id}/series_list/` - Get series for a publisher

### Common Query Parameters

- `?page=N` - Pagination
- `?name=search` - Name-based filtering
- `?modified_gt=2025-01-01T00:00:00Z` - Modified after date
- `?cv_id=12345` - Filter by Comic Vine ID
- `?gcd_id=67890` - Filter by Grand Comics Database ID

---

## Endpoints

### Arc

Story arcs that span multiple issues, often across different series.

**Base Path:** `/api/arc/`

**Actions:**

- `GET /api/arc/` - List all arcs
- `GET /api/arc/{id}/` - Retrieve arc details
- `POST /api/arc/` - Create new arc (requires editor or admin)
- `PUT/PATCH /api/arc/{id}/` - Update arc (requires editor or admin)
- `GET /api/arc/{id}/issue_list/` - List issues in this arc

**Filters:**

- `name` - Arc name (case-insensitive, partial match)
- `cv_id` - Comic Vine ID (exact match)
- `gcd_id` - Grand Comics Database ID (exact match)
- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "name": "Secret Wars",
  "slug": "secret-wars",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `desc` - Description
    - `image` - Cover image URL
    - `cv_id` - Comic Vine ID
    - `gcd_id` - Grand Comics Database ID
    - `resource_url` - Link to web UI

**Example:**
```bash
# Get all arcs with "secret" in the name
GET /api/arc/?name=secret

# Get issues in an arc
GET /api/arc/123/issue_list/
```

---

### Character

Comic book characters appearing in issues.

**Base Path:** `/api/character/`

**Actions:**

- `GET /api/character/` - List all characters
- `GET /api/character/{id}/` - Retrieve character details
- `POST /api/character/` - Create new character (requires editor or admin)
- `PUT/PATCH /api/character/{id}/` - Update character (requires editor or admin)
- `GET /api/character/{id}/issue_list/` - List issues featuring this character

**Filters:**

- `name` - Character name (case-insensitive, partial match)
- `cv_id` - Comic Vine ID (exact match)
- `gcd_id` - Grand Comics Database ID (exact match)
- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "name": "Spider-Man",
  "slug": "spider-man",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `alias` - Character aliases
    - `desc` - Description
    - `image` - Character image URL
    - `creators` - Array of creator objects
    - `teams` - Array of team objects
    - `universes` - Array of universe objects
    - `cv_id` - Comic Vine ID
    - `gcd_id` - Grand Comics Database ID
    - `resource_url` - Link to web UI

**Example:**
```bash
# Find Spider-Man
GET /api/character/?name=spider-man

# Get all issues featuring a character
GET /api/character/456/issue_list/
```

---

### Creator

Writers, artists, and other comic book creators.

**Base Path:** `/api/creator/`

**Actions:**

- `GET /api/creator/` - List all creators
- `GET /api/creator/{id}/` - Retrieve creator details
- `POST /api/creator/` - Create new creator (requires editor or admin)
- `PUT/PATCH /api/creator/{id}/` - Update creator (requires editor or admin)

**Filters:**

- `name` - Creator name (case-insensitive, partial match)
- `cv_id` - Comic Vine ID (exact match)
- `gcd_id` - Grand Comics Database ID (exact match)
- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "name": "Stan Lee",
  "slug": "stan-lee",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `desc` - Biography
    - `birth` - Birth date
    - `death` - Death date
    - `image` - Creator photo URL
    - `cv_id` - Comic Vine ID
    - `gcd_id` - Grand Comics Database ID
    - `resource_url` - Link to web UI

**Example:**
```bash
# Find creators by name
GET /api/creator/?name=lee

# Get creator details
GET /api/creator/789/
```

---

### Issue

Individual comic book issues.

**Base Path:** `/api/issue/`

**Actions:**

- `GET /api/issue/` - List all issues
- `GET /api/issue/{id}/` - Retrieve issue details
- `POST /api/issue/` - Create new issue (requires editor or admin)
- `PUT/PATCH /api/issue/{id}/` - Update issue (requires editor or admin)

**Extensive Filtering:**

The Issue endpoint supports the most comprehensive filtering options:

**Date Filters:**

- `store_date` - Store date (exact match, YYYY-MM-DD)
- `store_date_range_after` - Store date on or after
- `store_date_range_before` - Store date on or before
- `foc_date` - Final order cutoff date (exact match)
- `foc_date_range_after` - FOC date on or after
- `foc_date_range_before` - FOC date on or before
- `cover_year` - Cover date year
- `cover_month` - Cover date month (1-12)

**Series Filters:**

- `series_name` - Series name (searches all words, case-insensitive)
- `series_id` - Series Metron ID
- `series_volume` - Series volume number
- `series_year_began` - Series start year

**Publisher/Imprint Filters:**

- `publisher_name` - Publisher name (partial match)
- `publisher_id` - Publisher Metron ID
- `imprint_name` - Imprint name (partial match)
- `imprint_id` - Imprint Metron ID

**Issue Identification:**

- `number` - Issue number (case-insensitive, exact match)
- `alt_number` - Alternate number (case-insensitive, exact match)
- `sku` - Distributor SKU (exact match)
- `upc` - UPC code (exact match)
- `cv_id` - Comic Vine ID
- `gcd_id` - Grand Comics Database ID
- `missing_cv_id` - Boolean, issues without Comic Vine ID
- `missing_gcd_id` - Boolean, issues without GCD ID
- `cover_hash` - Perceptual hash for cover matching

**Content Filters:**

- `rating` - Content rating (exact match)

**Metadata:**

- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "series": {
    "id": 100,
    "name": "Amazing Spider-Man",
    "volume": 1,
    "series_type": {
      "id": 1,
      "name": "Ongoing Series"
    }
  },
  "number": "1",
  "cover_date": "1963-03-01",
  "store_date": "1963-01-10",
  "image": "https://example.com/covers/issue-1.jpg",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `desc` - Issue description
    - `price` - Cover price
    - `sku` - Distributor SKU
    - `isbn` - ISBN number
    - `upc` - UPC code
    - `page_count` - Number of pages
    - `rating` - Content rating object
    - `arcs` - Story arcs
    - `characters` - Characters appearing
    - `teams` - Teams appearing
    - `universes` - Universes
    - `credits` - Creator credits with roles
    - `variants` - Variant covers
    - `reprints` - Reprinted issues
    - `cv_id` - Comic Vine ID
    - `gcd_id` - Grand Comics Database ID
    - `cover_hash` - Perceptual image hash
    - `foc_date` - Final order cutoff date
    - `resource_url` - Link to web UI

**Cover Hash:**
The `cover_hash` field contains a perceptual hash generated using [ImageHash](https://github.com/JohannesBuchner/imagehash). This allows for finding similar or duplicate covers.

**Examples:**
```bash
# Get issues from January 2025
GET /api/issue/?store_date_range_after=2025-01-01&store_date_range_before=2025-01-31

# Find issues by series name
GET /api/issue/?series_name=amazing spider-man

# Get issues from a specific publisher
GET /api/issue/?publisher_name=marvel

# Find issues without Comic Vine IDs
GET /api/issue/?missing_cv_id=true

# Search by cover year and month
GET /api/issue/?cover_year=2024&cover_month=12

# Find by UPC
GET /api/issue/?upc=75960609558200111
```

---

### Publisher

Comic book publishers.

**Base Path:** `/api/publisher/`

**Actions:**

- `GET /api/publisher/` - List all publishers
- `GET /api/publisher/{id}/` - Retrieve publisher details
- `POST /api/publisher/` - Create new publisher (requires editor or admin)
- `PUT/PATCH /api/publisher/{id}/` - Update publisher (requires editor or admin)
- `GET /api/publisher/{id}/series_list/` - List series from this publisher

**Filters:**

- `name` - Publisher name (case-insensitive, partial match)
- `cv_id` - Comic Vine ID (exact match)
- `gcd_id` - Grand Comics Database ID (exact match)
- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "name": "Marvel Comics",
  "slug": "marvel-comics",
  "founded": 1939,
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `desc` - Description
    - `image` - Publisher logo URL
    - `cv_id` - Comic Vine ID
    - `gcd_id` - Grand Comics Database ID
    - `resource_url` - Link to web UI

**Example:**
```bash
# Get all publishers
GET /api/publisher/

# Get series from a publisher
GET /api/publisher/1/series_list/
```

---

### Imprint

Publisher imprints (e.g., Vertigo, MAX).

**Base Path:** `/api/imprint/`

**Actions:**

- `GET /api/imprint/` - List all imprints
- `GET /api/imprint/{id}/` - Retrieve imprint details
- `POST /api/imprint/` - Create new imprint (requires editor or admin)
- `PUT/PATCH /api/imprint/{id}/` - Update imprint (requires editor or admin)

**Filters:**

- `name` - Imprint name (case-insensitive, partial match)
- `cv_id` - Comic Vine ID (exact match)
- `gcd_id` - Grand Comics Database ID (exact match)
- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "name": "Vertigo",
  "slug": "vertigo",
  "founded": 1993,
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `publisher` - Parent publisher object
    - `desc` - Description
    - `image` - Imprint logo URL
    - `cv_id` - Comic Vine ID
    - `gcd_id` - Grand Comics Database ID
    - `resource_url` - Link to web UI

**Example:**
```bash
# Find imprints
GET /api/imprint/?name=vertigo
```

---

### Series

Comic book series.

**Base Path:** `/api/series/`

**Actions:**

- `GET /api/series/` - List all series
- `GET /api/series/{id}/` - Retrieve series details
- `POST /api/series/` - Create new series (requires editor or admin)
- `PUT/PATCH /api/series/{id}/` - Update series (requires editor or admin)
- `GET /api/series/{id}/issue_list/` - List issues in this series

**Extensive Filtering:**

**Basic Filters:**

- `name` - Series name (searches all words, case-insensitive)
- `volume` - Volume number
- `year_began` - Year series started
- `year_end` - Year series ended

**Publisher/Imprint:**

- `publisher_id` - Publisher Metron ID
- `publisher_name` - Publisher name (partial match)
- `imprint_name` - Imprint name (partial match)

**Series Type:**

- `series_type_id` - Series type Metron ID
- `series_type` - Series type name (partial match)

**Status:**

- `status` - Series status (choices: continuing, completed, cancelled, hiatus)

**External IDs:**

- `cv_id` - Comic Vine ID
- `missing_cv_id` - Boolean, series without Comic Vine ID
- `gcd_id` - Grand Comics Database ID
- `missing_gcd_id` - Boolean, series without GCD ID

**Metadata:**

- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "series_type": {
    "id": 1,
    "name": "Ongoing Series"
  },
  "publisher": {
    "id": 10,
    "name": "Marvel Comics"
  },
  "name": "Amazing Spider-Man",
  "volume": 1,
  "year_began": 1963,
  "year_end": null,
  "issue_count": 900,
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `imprint` - Imprint object (if applicable)
    - `status` - Series status (continuing, completed, cancelled, hiatus)
    - `desc` - Description
    - `genres` - Array of genre objects
    - `associated` - Associated series
    - `cv_id` - Comic Vine ID
    - `gcd_id` - Grand Comics Database ID
    - `resource_url` - Link to web UI

**Series Status Choices:**

- `continuing` - Ongoing series
- `completed` - Finished series
- `cancelled` - Cancelled series
- `hiatus` - On hiatus

**Examples:**
```bash
# Search for series by name (all words must match)
GET /api/series/?name=amazing spider-man

# Get Marvel ongoing series
GET /api/series/?publisher_name=marvel&status=continuing

# Find series by type
GET /api/series/?series_type=mini-series

# Get series from a specific year
GET /api/series/?year_began=2020

# Get issues in a series
GET /api/series/123/issue_list/
```

---

### Team

Superhero teams and groups.

**Base Path:** `/api/team/`

**Actions:**

- `GET /api/team/` - List all teams
- `GET /api/team/{id}/` - Retrieve team details
- `POST /api/team/` - Create new team (requires editor or admin)
- `PUT/PATCH /api/team/{id}/` - Update team (requires editor or admin)
- `GET /api/team/{id}/issue_list/` - List issues featuring this team

**Filters:**

- `name` - Team name (case-insensitive, partial match)
- `cv_id` - Comic Vine ID (exact match)
- `gcd_id` - Grand Comics Database ID (exact match)
- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "name": "Avengers",
  "slug": "avengers",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `desc` - Description
    - `image` - Team image URL
    - `creators` - Array of creator objects
    - `universes` - Array of universe objects
    - `cv_id` - Comic Vine ID
    - `gcd_id` - Grand Comics Database ID
    - `resource_url` - Link to web UI

**Example:**
```bash
# Find teams
GET /api/team/?name=avengers

# Get issues featuring a team
GET /api/team/789/issue_list/
```

---

### Universe

Comic book universes (e.g., Earth-616, Earth-1).

**Base Path:** `/api/universe/`

**Actions:**

- `GET /api/universe/` - List all universes
- `GET /api/universe/{id}/` - Retrieve universe details
- `POST /api/universe/` - Create new universe (requires editor or admin)
- `PUT/PATCH /api/universe/{id}/` - Update universe (requires editor or admin)

**Filters:**

- `name` - Universe name (case-insensitive, partial match)
- `designation` - Universe designation (case-insensitive, partial match)
- `modified_gt` - Modified after datetime

**List Response Fields:**
```json
{
  "id": 1,
  "name": "Earth-616",
  "slug": "earth-616",
  "designation": "616",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `publisher` - Publisher object
    - `desc` - Description
    - `image` - Universe image URL
    - `resource_url` - Link to web UI

**Example:**
```bash
# Find universes by designation
GET /api/universe/?designation=616
```

---

### Reading List

User-created reading lists that organize issues in a specific reading order.

**Base Path:** `/api/reading_list/`

**Actions:**

- `GET /api/reading_list/` - List accessible reading lists
- `GET /api/reading_list/{id}/` - Retrieve reading list details
- `GET /api/reading_list/{id}/items/` - Get issues in a reading list

**Read-Only API:**
This endpoint is read-only. Create, update, and delete operations are not available via the API. Use the web interface to manage reading lists.

**Filters:**

- `name` - Reading list name (case-insensitive, partial match)
- `user` - User ID (exact match)
- `username` - Username (case-insensitive, partial match)
- `attribution_source` - Attribution source code (exact match)
- `is_private` - Boolean, filter by privacy status
- `modified_gt` - Modified after datetime

**Attribution Source Codes:**

- `CBRO` - Comic Book Reading Orders
- `CMRO` - Complete Marvel Reading Orders
- `CBH` - Comic Book Herald
- `CBT` - Comic Book Treasury
- `MG` - Marvel Guides
- `HTLC` - How To Love Comics
- `LOCG` - League of ComicGeeks
- `OTHER` - Other

**List Response Fields:**
```json
{
  "id": 1,
  "name": "Secret Wars (2015)",
  "slug": "secret-wars-2015",
  "user": {
    "id": 5,
    "username": "johndoe"
  },
  "is_private": false,
  "attribution_source": "CBRO",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Detail Response Fields:**

- All list fields plus:
    - `desc` - Description
    - `attribution_source` - Full attribution source name (e.g., "Comic Book Reading Orders")
    - `attribution_url` - URL to source
    - `items_url` - URL to fetch reading list items
    - `resource_url` - Link to web UI

**Items Response Fields:**
```json
{
  "id": 101,
  "issue": {
    "id": 5432,
    "series": {
      "id": 789,
      "name": "Secret Wars",
      "volume": 1,
      "series_type": {
        "id": 1,
        "name": "Mini-Series"
      }
    },
    "number": "1",
    "cover_date": "2015-07-01",
    "store_date": "2015-05-06",
    "cv_id": 123456,
    "gcd_id": null,
    "modified": "2025-01-10T14:20:00Z"
  },
  "order": 1
}
```

**Permissions:**

*List Endpoint:*
- **Unauthenticated users:** Returns 401 Unauthorized
- **Authenticated users:** Public lists + own lists (public and private)
- **Admin users:** Public lists + own lists + Metron user's lists

*Detail/Items Endpoints:*
A user can access a reading list if:
- The list is public (is_private=false), OR
- The user owns the list, OR
- The user is an admin AND the list belongs to the "Metron" user

Access denied returns `404 Not Found`.

**Pagination:**

- Default page size: 50 items per page for lists and items
- Items are ordered by the `order` field

**Examples:**
```bash
# List all accessible reading lists
GET /api/reading_list/

# Find public reading lists
GET /api/reading_list/?is_private=false

# Find lists by username
GET /api/reading_list/?username=johndoe

# Find lists from Comic Book Reading Orders
GET /api/reading_list/?attribution_source=CBRO

# Get reading list details
GET /api/reading_list/1/

# Get items in a reading list
GET /api/reading_list/1/items/

# Combine multiple filters
GET /api/reading_list/?name=secret&is_private=false
```

**Notes:**

- When filtering, use attribution source codes (e.g., `CBRO`). In detail responses, the full name is returned (e.g., "Comic Book Reading Orders")
- Items endpoint excludes `image` and `cover_hash` from issue data for performance
- Some lists belong to a special "Metron" user account representing curated/official reading orders
- Admin users have special access to Metron user's lists

---

### Supporting Resources

#### Role

Creator roles (e.g., Writer, Penciller, Inker).

**Base Path:** `/api/role/`

**Actions:**

- `GET /api/role/` - List all roles (read-only)

**Filters:**

- `name` - Role name (case-insensitive, partial match)
- `modified_gt` - Modified after datetime

**Response Fields:**
```json
{
  "id": 1,
  "name": "Writer"
}
```

---

#### Series Type

Types of comic series (e.g., Ongoing, Mini-Series, One-Shot).

**Base Path:** `/api/series_type/`

**Actions:**

- `GET /api/series_type/` - List all series types (read-only)

**Filters:**

- `name` - Series type name (case-insensitive, partial match)
- `modified_gt` - Modified after datetime

**Response Fields:**
```json
{
  "id": 1,
  "name": "Ongoing Series"
}
```

---

#### Credit

Creator credits for issues.

**Base Path:** `/api/credit/`

**Actions:**

- `POST /api/credit/` - Create new credits (requires editor or admin, bulk creation supported)

**Request Format:**
```json
[
  {
    "issue": 123,
    "creator": 456,
    "role": [1, 2]
  }
]
```

**Notes:**

- Accepts arrays for bulk creation
- `issue` - Issue ID
- `creator` - Creator ID
- `role` - Array of role IDs

---

#### Variant

Variant covers for issues.

**Base Path:** `/api/variant/`

**Actions:**

- `POST /api/variant/` - Create new variant (requires editor or admin, requires image upload)
- `PUT/PATCH /api/variant/{id}/` - Update variant (requires editor or admin)

**Fields:**

- `issue` - Parent issue ID
- `name` - Variant name
- `sku` - Distributor SKU
- `upc` - UPC code
- `image` - Variant cover image

---

## Filtering

### Common Filter Patterns

**Name Searching:**

- Case-insensitive partial matching
- Accent-insensitive (unaccent lookup)
- Example: `?name=spider` matches "Spider-Man", "spider-woman"

**Series Name Searching:**

- Searches for all words in the query
- Example: `?series_name=amazing spider-man` requires all three words

**Date Filtering:**

- `modified_gt` - Find items modified after a specific datetime
- Format: ISO 8601 (YYYY-MM-DDTHH:MM:SSZ)
- Example: `?modified_gt=2025-01-01T00:00:00Z`

**Date Range Filtering:**

- `{field}_range_after` - On or after date
- `{field}_range_before` - On or before date
- Example: `?store_date_range_after=2025-01-01&store_date_range_before=2025-01-31`

**Boolean Filters:**

- `missing_cv_id` - True/false for missing Comic Vine IDs
- `missing_gcd_id` - True/false for missing GCD IDs
- Example: `?missing_cv_id=true`

**Combining Filters:**
Multiple filters can be combined with `&`:
```bash
GET /api/issue/?series_name=spider-man&cover_year=2024&publisher_name=marvel
```

---

## Pagination

All list endpoints return paginated responses.

**Response Structure:**
```json
{
  "count": 1500,
  "next": "https://metron.cloud/api/issue/?page=2",
  "previous": null,
  "results": [...]
}
```

**Fields:**

- `count` - Total number of items
- `next` - URL to next page (null if last page)
- `previous` - URL to previous page (null if first page)
- `results` - Array of items for current page

**Navigation:**
```bash
# First page (default)
GET /api/issue/

# Second page
GET /api/issue/?page=2

# With filters
GET /api/issue/?series_name=spider-man&page=3
```

**Page Size:**

- Default page size varies by endpoint (typically 25-100 items)
- Some endpoints may allow custom page size via `?page_size=N`

---

## Error Handling

### Common HTTP Status Codes

**Success Codes:**

- `200 OK` - Request succeeded
- `201 Created` - Resource created successfully
- `204 No Content` - Delete succeeded

**Client Error Codes:**

- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource doesn't exist

**Server Error Codes:**

- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Field Validation Errors:**
```json
{
  "field_name": ["Error message for this field"],
  "another_field": ["Another error message"]
}
```

### Common Errors

**401 Unauthorized:**
```json
{
  "detail": "Authentication credentials were not provided."
}
```
Solution: Include authentication credentials in your request.

**403 Forbidden:**
```json
{
  "detail": "You do not have permission to perform this action."
}
```
Solution: Ensure you have the required permissions for this operation.

**404 Not Found:**
```json
{
  "detail": "Not found."
}
```
Solution: Check that the resource ID is correct.

---

## Rate Limiting

The API implements rate limiting to ensure fair usage. Rate limit details:

- Limits are applied per user/IP address
- Rate limit information is included in response headers:
    - `X-RateLimit-Limit` - Requests allowed per time period
    - `X-RateLimit-Remaining` - Requests remaining
    - `X-RateLimit-Reset` - Time when limit resets

If you exceed the rate limit, you'll receive a `429 Too Many Requests` response.

---

## Additional Resources

### Interactive Documentation

- **Swagger UI:** `/docs/` - Interactive API documentation with test capabilities
- **OpenAPI Schema:** `/api/schema/` - Machine-readable API specification

### Web Interface

- **Browse Comics:** Visit the main site to browse the database
- **API Authentication:** `/api-auth/login/` - Log in for session authentication

### External Integrations

The API supports mapping to external databases:

- **Comic Vine:** Use `cv_id` fields for Comic Vine integration
- **Grand Comics Database:** Use `gcd_id` fields for GCD integration

### Best Practices

1. **Use Filtering:** Apply filters to reduce response size and improve performance
2. **Respect Rate Limits:** Implement backoff strategies if rate limited
3. **Handle Pagination:** Process all pages when retrieving complete datasets
4. **Cache Responses:** Cache data when appropriate to reduce API calls
5. **Use Modified Dates:** Use `modified_gt` to sync only changed data
6. **Include User-Agent:** Identify your application in the User-Agent header
7. **Handle Errors Gracefully:** Implement proper error handling and retries

### Example Client Code

**Python:**
```python
import requests

class MetronAPI:
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.auth = (username, password)

    def get_issues(self, **filters):
        response = requests.get(
            f"{self.base_url}/issue/",
            auth=self.auth,
            params=filters
        )
        response.raise_for_status()
        return response.json()

    def get_all_pages(self, endpoint, **filters):
        """Get all pages of results"""
        results = []
        url = f"{self.base_url}/{endpoint}/"

        while url:
            response = requests.get(url, auth=self.auth, params=filters)
            response.raise_for_status()
            data = response.json()
            results.extend(data['results'])
            url = data['next']
            filters = {}  # Clear params after first request

        return results

# Usage
api = MetronAPI("https://metron.cloud/api", "your-username", "your-password")
issues = api.get_issues(series_name="spider-man", cover_year=2024)
```

**JavaScript:**
```javascript
class MetronAPI {
  constructor(baseUrl, username, password) {
    this.baseUrl = baseUrl;
    const credentials = btoa(`${username}:${password}`);
    this.headers = {
      'Authorization': `Basic ${credentials}`,
      'Content-Type': 'application/json'
    };
  }

  async getIssues(filters = {}) {
    const params = new URLSearchParams(filters);
    const response = await fetch(
      `${this.baseUrl}/issue/?${params}`,
      { headers: this.headers }
    );

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return await response.json();
  }

  async *getAllPages(endpoint, filters = {}) {
    let url = `${this.baseUrl}/${endpoint}/`;
    const params = new URLSearchParams(filters);

    while (url) {
      const response = await fetch(
        `${url}${url.includes('?') ? '&' : '?'}${params}`,
        { headers: this.headers }
      );

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      yield data.results;
      url = data.next;
    }
  }
}

// Usage
const api = new MetronAPI('https://metron.cloud/api', 'your-username', 'your-password');
const issues = await api.getIssues({ series_name: 'spider-man', cover_year: 2024 });
```

---

## Support and Feedback

For questions, issues, or feature requests:

- **GitHub Issues:** Report bugs or request features
- **Documentation:** Refer to the Swagger UI at `/docs/` for endpoint details
- **Web Interface:** Use the main site for browsing and manual data entry

---

## Changelog

### Version 1.0
- Initial API release
- Support for all major comic book resources
- Advanced filtering and pagination
- Image upload support
- External ID mapping

