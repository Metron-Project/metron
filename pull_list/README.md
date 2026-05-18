# Pull List - User Guide

The Pull List feature lets you track ongoing comic book series you follow, mirroring a traditional comic shop pull list. Add series to your list and see upcoming issues at a glance so you never miss a new release.

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
- [Usage Examples](#usage-examples)
- [URLs Quick Reference](#urls-quick-reference)
- [Tips and Best Practices](#tips-and-best-practices)

## Features

- **Track Series**: Add ongoing series you follow to a single, private list
- **Upcoming Issues**: Automatically see issues with a future store date for series on your list
- **Remove Series**: Drop series you no longer follow at any time
- **Privacy**: Your pull list is completely private to you

## Getting Started

### Viewing Your Pull List

Visit `/pull-list/` to see your pull list. The page is divided into two panels:

- **Series on Pull List** — every series you are currently following
- **Upcoming Issues** — issues with a store date on or after today, drawn from your series

Your pull list is created automatically the first time you visit the page.

### Adding a Series

1. Log in to your account
2. Navigate to `/pull-list/`
3. Use the search field to find a series by name
4. Click **Add**
5. The series appears immediately in the "Series on Pull List" table

### Removing a Series

1. Navigate to `/pull-list/`
2. Click the **Remove** button next to the series you want to drop
3. Confirm the removal on the confirmation page

## Usage Examples

### Keeping Up with New Releases

1. Add every ongoing series you follow to your pull list
2. Visit `/pull-list/` each week to see what is shipping
3. The Upcoming Issues panel shows store dates so you know exactly when to pick up each issue
4. When a series ends or you lose interest, remove it from your list

### Discovering Gaps

If an expected issue does not appear in Upcoming Issues, the issue may not yet have a store date entered in the database. Check back later or visit the series page directly.

## URLs Quick Reference

| URL | Purpose | Login Required |
|-----|---------|----------------|
| `/pull-list/` | View your pull list and add series | Yes |
| `/pull-list/remove/<series_id>/` | Remove a series from your pull list | Yes* |

*Must be the owner of the pull list.

## Tips and Best Practices

1. **Add series early**: Add a series as soon as you start reading it so you never miss an issue
2. **Clean up regularly**: Remove series that have ended or that you have dropped to keep Upcoming Issues focused
3. **Combine with Wish List**: Use the [Wish List](../wish_list/README.md) to track specific back issues you want — the pull list is for ongoing titles only
4. **Upcoming Issues lag**: Store dates are only as accurate as the data in Metron; check the series page if an issue seems missing

---

For API documentation, see the main [API README](../api/README.md).
