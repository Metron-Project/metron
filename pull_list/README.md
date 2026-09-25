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
- **Upcoming Issues**: See issues with a future store date for series on your list, grouped by release day
- **Final Order Cutoff Warnings**: Get a reminder when an issue's final order cutoff (FOC) is coming up, so you can tell your shop in time
- **Filter by Series**: Focus the upcoming list on a single series
- **List or Cover View**: Browse upcoming issues as a compact list or as a grid of covers
- **Remove with Undo**: Drop series you no longer follow, with a one-click undo if you remove one by mistake
- **Privacy**: Your pull list is completely private to you

## Getting Started

### Viewing Your Pull List

Visit `/pull-list/` to see your pull list. Your pull list is created automatically the first time you visit the page.

The header shows how many series you follow, how many issues are coming up, and the date of the next release. Below it the page is divided into two panels:

- **Upcoming issues** — issues with a store date on or after today, drawn from your series and grouped by release day (e.g. "Wednesday, October 1 · In 6 days · 3 issues"). Up to 50 issues are shown at a time.
- **Series** — every series you are following, with the date of its next issue

Use the list and cover buttons at the top of the Upcoming issues panel to switch between a compact list and a grid of covers.

### Final Order Cutoff

Comic shops need to place their orders before a publisher's final order cutoff (FOC) date. Each issue with an FOC date shows a tag:

- **Yellow tag** — the cutoff is within the next 7 days. These issues are also listed in a warning banner at the top of the page, grouped by cutoff date, so you can let your shop know in time.
- **Blue tag** — the cutoff is further away.

The warning banner always covers your whole pull list, even when you are filtering by a single series.

### Filtering by Series

Select a series in the **Series** panel to show only its upcoming issues. To show all series again, select the same series again, or click **Clear filter** at the top of the panel.

### Adding a Series

1. Log in to your account
2. Navigate to `/pull-list/`
3. Use the **Add a series** search field at the top of the page to find a series by name
4. Click **Add**
5. The series appears in the Series panel, and its upcoming issues are added to the list

You can also add or remove a series with the **Pull List** button on any series page.

### Removing a Series

1. Navigate to `/pull-list/`
2. Click the **×** button next to the series in the Series panel
3. The series is removed immediately, and a notification appears with an **Undo** button in case you removed it by mistake

Your current series filter and view are kept after removing a series (unless you removed the series you were filtering on).

## Usage Examples

### Keeping Up with New Releases

1. Add every ongoing series you follow to your pull list
2. Visit `/pull-list/` each week to see what is shipping
3. The Upcoming issues panel groups issues by store date so you know exactly when to pick up each one
4. Watch for the final order cutoff banner and let your shop know about any issues you want before the cutoff
5. When a series ends or you lose interest, remove it from your list

### Discovering Gaps

If an expected issue does not appear in Upcoming issues, the issue may not yet have a store date entered in the database. Check back later or visit the series page directly. A series with no upcoming issues shows "No upcoming issues" in the Series panel.

## URLs Quick Reference

| URL | Purpose | Login Required |
|-----|---------|----------------|
| `/pull-list/` | View your pull list and add series | Yes |
| `/pull-list/?series=<series_id>` | Show upcoming issues for one series on your list | Yes |
| `/pull-list/?view=covers` | Show upcoming issues as covers (`view=list` for the list) | Yes |
| `/pull-list/remove/<series_id>/` | Remove a series from your pull list | Yes* |
| `/pull-list/toggle/<series_slug>/` | Add or remove a series (used by the button on series pages; POST only) | Yes |

The `series` and `view` parameters can be combined, e.g. `/pull-list/?series=42&view=covers`.

*Only series on your own pull list can be removed.

## Tips and Best Practices

1. **Add series early**: Add a series as soon as you start reading it so you never miss an issue
2. **Clean up regularly**: Remove series that have ended or that you have dropped to keep Upcoming issues focused
3. **Combine with Wish List**: Use the [Wish List](../wish_list/README.md) to track specific back issues you want — the pull list is for ongoing titles only
4. **Upcoming issues lag**: Store and FOC dates are only as accurate as the data in Metron; check the series page if an issue seems missing
5. **Bookmark a view**: Filter and view choices are part of the URL, so you can bookmark your favourite view

---

For API documentation, see the main [API README](../api/README.md).
