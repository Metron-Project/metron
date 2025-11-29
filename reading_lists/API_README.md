# Reading List API Documentation

This document provides comprehensive information about the Reading List API endpoints in Metron.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoints](#endpoints)
  - [List Reading Lists](#list-reading-lists)
  - [Retrieve Reading List](#retrieve-reading-list)
  - [Get Reading List Items](#get-reading-list-items)
- [Filtering](#filtering)
- [Permissions](#permissions)
- [Response Structures](#response-structures)
- [Example Requests](#example-requests)
- [Error Responses](#error-responses)

## Overview

The Reading List API provides read-only access to reading lists in Metron. Users can list reading lists, retrieve detailed information about specific lists, and access the items (issues) within a reading list.

**Key Features:**
- Read-only API (no create, update, or delete operations via API)
- Authentication required for all endpoints
- Permission-based access to private lists
- Paginated responses
- Comprehensive filtering options
- Nested serializers for related data

## Authentication

All Reading List API endpoints require authentication.

**Unauthenticated Requests:**
All endpoints return `401 Unauthorized` for unauthenticated requests.

## Base URL

```
https://metron.cloud/api/reading_list/
```

## Endpoints

### List Reading Lists

Retrieve a paginated list of reading lists based on user permissions.

**Endpoint:**
```
GET /api/reading_list/
```

**Permissions:**
- **Unauthenticated users:** Returns 401 Unauthorized
- **Authenticated users:** Public lists + own lists (public and private)
- **Admin users:** Public lists + own lists + Metron user's lists (public and private)

**Query Parameters:**
See [Filtering](#filtering) section for available filters.

**Response:**
```json
{
  "count": 150,
  "next": "https://metron.cloud/api/reading_list/?page=2",
  "previous": null,
  "results": [
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
  ]
}
```

**Pagination:**
- Default page size: 50 items per page
- Use `?page=N` to navigate pages

---

### Retrieve Reading List

Get detailed information about a specific reading list.

**Endpoint:**
```
GET /api/reading_list/{id}/
```

**Path Parameters:**
- `id` (integer): The reading list ID

**Permissions:**
- User can access the list if:
  - The list is public, OR
  - The user owns the list, OR
  - The user is an admin and the list belongs to the Metron user

**Response:**
```json
{
  "id": 1,
  "user": {
    "id": 5,
    "username": "johndoe"
  },
  "name": "Secret Wars (2015)",
  "slug": "secret-wars-2015",
  "desc": "Complete reading order for the 2015 Secret Wars event",
  "is_private": false,
  "attribution_source": "Comic Book Reading Orders",
  "attribution_url": "https://example.com/reading-order",
  "items_url": "https://metron.cloud/api/reading_list/1/items/",
  "resource_url": "https://metron.cloud/reading-lists/secret-wars-2015/",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Error Responses:**
- `401 Unauthorized`: Not authenticated
- `404 Not Found`: Reading list doesn't exist or user doesn't have permission

---

### Get Reading List Items

Retrieve a paginated list of issues in a reading list.

**Endpoint:**
```
GET /api/reading_list/{id}/items/
```

**Path Parameters:**
- `id` (integer): The reading list ID

**Permissions:**
- Same as Retrieve Reading List

**Response:**
```json
{
  "count": 45,
  "next": "https://metron.cloud/api/reading_list/1/items/?page=2",
  "previous": null,
  "results": [
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
  ]
}
```

**Pagination:**
- Default page size: 50 items per page
- Use `?page=N` to navigate pages
- Items are ordered by the `order` field

**Notes:**
- Issues are returned in the order specified by the reading list
- Each item includes nested issue and series data
- Image and cover_hash are excluded from issue data for performance

---

## Filtering

The List Reading Lists endpoint supports the following query parameters:

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `name` | string | Filter by reading list name (case-insensitive, partial match) | `?name=secret` |
| `user` | integer | Filter by user ID | `?user=5` |
| `username` | string | Filter by username (case-insensitive, partial match) | `?username=john` |
| `attribution_source` | string | Filter by attribution source code | `?attribution_source=CBRO` |
| `is_private` | boolean | Filter by privacy status | `?is_private=false` |
| `modified_gt` | datetime | Filter lists modified after this date/time | `?modified_gt=2025-01-01T00:00:00Z` |

**Attribution Source Codes:**
- `CBRO` - Comic Book Reading Orders
- `CMRO` - Complete Marvel Reading Orders
- `CBH` - Comic Book Herald
- `CBT` - Comic Book Treasury
- `MG` - Marvel Guides
- `HTLC` - How To Love Comics
- `LOCG` - League of ComicGeeks
- `OTHER` - Other

**Examples:**

```bash
# Find all public reading lists
GET /api/reading_list/?is_private=false

# Find reading lists by a specific user
GET /api/reading_list/?username=johndoe

# Find lists from Comic Book Reading Orders
GET /api/reading_list/?attribution_source=CBRO

# Find lists modified after a specific date
GET /api/reading_list/?modified_gt=2025-01-01T00:00:00Z

# Combine multiple filters
GET /api/reading_list/?name=secret&is_private=false
```

---

## Permissions

### Visibility Rules

**List Endpoint Visibility:**

| User Type | Can See |
|-----------|---------|
| Unauthenticated | None (401 error) |
| Authenticated User | Public lists + Own lists |
| Admin User | Public lists + Own lists + Metron user's lists |

**Detail/Items Endpoint Visibility:**

A user can access a reading list detail or items if:
1. The list is public (is_private=false), OR
2. The user owns the list, OR
3. The user is an admin AND the list belongs to the "Metron" user

**Access Denied:**
Returns `404 Not Found` if the user doesn't have permission to view the list.

### Read-Only API

The Reading List API is **read-only**. The following operations are not supported:
- `POST` (create)
- `PUT` (full update)
- `PATCH` (partial update)
- `DELETE` (delete)

These operations return `403 Forbidden` even for admin users. Use the web interface to manage reading lists.

---

## Response Structures

### ReadingListListSerializer

Used for the list endpoint (`/api/reading_list/`):

```json
{
  "id": 1,
  "name": "Reading List Name",
  "slug": "reading-list-name",
  "user": {
    "id": 5,
    "username": "johndoe"
  },
  "is_private": false,
  "attribution_source": "CBRO",
  "modified": "2025-01-15T10:30:00Z"
}
```

### ReadingListReadSerializer

Used for the detail endpoint (`/api/reading_list/{id}/`):

```json
{
  "id": 1,
  "user": {
    "id": 5,
    "username": "johndoe"
  },
  "name": "Reading List Name",
  "slug": "reading-list-name",
  "desc": "Description of the reading list",
  "is_private": false,
  "attribution_source": "Comic Book Reading Orders",
  "attribution_url": "https://example.com/source",
  "items_url": "https://metron.cloud/api/reading_list/1/items/",
  "resource_url": "https://metron.cloud/reading-lists/reading-list-name/",
  "modified": "2025-01-15T10:30:00Z"
}
```

**Notes:**
- `attribution_source` returns the human-readable display name (not the code)
- `items_url` provides the direct link to fetch the reading list items
- `resource_url` provides the link to the web UI detail page

### ReadingListItemSerializer

Used for the items endpoint (`/api/reading_list/{id}/items/`):

```json
{
  "id": 101,
  "issue": {
    "id": 5432,
    "series": {
      "id": 789,
      "name": "Series Name",
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

**Notes:**
- Issues are nested within each item
- `order` indicates the position in the reading list
- `image` and `cover_hash` are excluded for performance

---

## Example Requests

### Using curl

**List all accessible reading lists:**
```bash
curl -X GET https://metron.cloud/api/reading_list/ \
  -H "Authorization: Basic base64-authorization-string"
```

**Get a specific reading list:**
```bash
curl -X GET https://metron.cloud/api/reading_list/1/ \
  -H "Authorization: Basic base64-authorization-string"
```

**Get items in a reading list:**
```bash
curl -X GET https://metron.cloud/api/reading_list/1/items/ \
  -H "Authorization: Basic base64-authorization-string"
```

**Filter reading lists by name:**
```bash
curl -X GET "https://metron.cloud/api/reading_list/?name=secret" \
  -H "Authorization: Basic base64-authorization-string"
```

### Using Python (requests library)

```python
import requests

# Configuration
BASE_URL = "https://metron.cloud/api"
headers = {"Authorization": "Basic base64-authorization-string"}

# List reading lists
response = requests.get(f"{BASE_URL}/reading_list/", headers=headers)
reading_lists = response.json()

# Get specific reading list
response = requests.get(f"{BASE_URL}/reading_list/1/", headers=headers)
reading_list = response.json()

# Get reading list items
response = requests.get(f"{BASE_URL}/reading_list/1/items/", headers=headers)
items = response.json()

# Filter by username
params = {"username": "johndoe"}
response = requests.get(f"{BASE_URL}/reading_list/", headers=headers, params=params)
user_lists = response.json()
```

### Using JavaScript (fetch)

```javascript
const BASE_URL = 'https://metron.cloud/api';
const headers = {
  'Authorization': 'Basic base64-authorization-string',
  'Content-Type': 'application/json'
};

// List reading lists
fetch(`${BASE_URL}/reading_list/`, { headers })
  .then(response => response.json())
  .then(data => console.log(data));

// Get specific reading list
fetch(`${BASE_URL}/reading_list/1/`, { headers })
  .then(response => response.json())
  .then(data => console.log(data));

// Get reading list items
fetch(`${BASE_URL}/reading_list/1/items/`, { headers })
  .then(response => response.json())
  .then(data => console.log(data));
```

---

## Error Responses

### 401 Unauthorized

**Reason:** User is not authenticated

```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Solution:** Provide valid authentication credentials

---

### 403 Forbidden

**Reason:** Attempting a write operation (POST, PUT, PATCH, DELETE)

```json
{
  "detail": "You do not have permission to perform this action."
}
```

**Solution:** Use the web interface for create, update, and delete operations

---

### 404 Not Found

**Reason:** Reading list doesn't exist or user doesn't have permission to view it

```json
{
  "detail": "Not found."
}
```

**Possible Causes:**
- Reading list ID is invalid
- Reading list is private and user is not the owner
- Reading list belongs to another user and is private

---

## Pagination

All list endpoints use pagination with the following structure:

```json
{
  "count": 150,
  "next": "https://metron.cloud/api/reading_list/?page=2",
  "previous": null,
  "results": [...]
}
```

**Fields:**
- `count`: Total number of items across all pages
- `next`: URL to the next page (null if on last page)
- `previous`: URL to the previous page (null if on first page)
- `results`: Array of items for the current page

**Page Size:**
- Reading list items: 50 per page
- Reading lists: Uses default pagination (typically 25-100 per page)

**Navigation:**
```bash
# First page
GET /api/reading_list/

# Second page
GET /api/reading_list/?page=2

# Third page
GET /api/reading_list/?page=3
```

---

## Notes

1. **Attribution Source Display:** When retrieving a reading list detail, the `attribution_source` field returns the human-readable name (e.g., "Comic Book Reading Orders") instead of the code (e.g., "CBRO"). When filtering, use the code.

2. **Performance:** The items endpoint is optimized with `select_related` to minimize database queries. Image data is excluded from issue serialization for better performance.

3. **Ordering:** Reading list items are always returned in the order specified by the `order` field, which reflects the intended reading sequence.

4. **Metron User:** Some reading lists belong to a special "Metron" user account. These represent curated/official reading orders. Admin users have special access to these lists.

5. **Read-Only:** This API is intentionally read-only. To create or modify reading lists, use the web interface at `/reading-lists/`.
