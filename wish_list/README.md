# Wish List - User Guide

The Wish List feature lets you track specific comic book issues you want to acquire — back issues, key issues, variants, or anything else on your radar. Set priorities, record the condition and price you are willing to pay, and mark items as acquired when you find them.

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
- [Usage Examples](#usage-examples)
- [Status Workflow](#status-workflow)
- [Priority System](#priority-system)
- [Grading and Price](#grading-and-price)
- [URLs Quick Reference](#urls-quick-reference)
- [Tips and Best Practices](#tips-and-best-practices)

## Features

- **Track Wanted Issues**: Add any issue to your private wish list
- **Priority Levels**: Rank items 1–5 so you focus on the most important finds first
- **Status Tracking**: Move items through Wanted → Found → Acquired
- **Condition Goals**: Set a minimum acceptable grade for each item
- **Budget Control**: Record the maximum price you are willing to pay
- **Collection Integration**: Acquiring an item automatically adds it to your collection
- **Privacy**: Your wish list is completely private to you

## Getting Started

### Viewing Your Wish List

Visit `/wish-list/` to see all your wanted items. Your wish list is created automatically the first time you visit.

Items are sorted by priority (1 first), then series name, then cover date.

### Adding an Issue

1. Log in to your account
2. Navigate to `/wish-list/`
3. Search for an issue using the autocomplete field (format: *Series Name (Year) #Number*)
4. Set optional details:
    - **Priority**: 1 (highest) to 5 (lowest)
    - **Status**: Wanted, Found, or Acquired
    - **Minimum Grade**: Lowest acceptable CGC grade
    - **Maximum Price**: Most you are willing to pay
5. Click **Add to Wish List**

### Removing an Issue

Click the trash icon next to any item, then confirm the deletion on the confirmation page.

## Usage Examples

### Hunting Back Issues

1. Add every issue you are looking for with status **Wanted** and priority based on how urgently you need it
2. Set a minimum grade if condition matters (e.g., 6.0 for reading copies, 9.4 for display)
3. Set a maximum price to avoid overpaying at shows or shops
4. When you spot an issue at a shop, update it to **Found**
5. When you buy it, click **Acquire** to record purchase details and add it to your collection

### Planning Convention Purchases

1. Before a convention, review your wish list filtered by high priority items (1–2)
2. Use the Minimum Grade and Maximum Price columns as your buying guide
3. Mark items as Found or Acquired on the spot (via mobile browser)

### Completing a Run

1. Add all missing issues from a series with equal priority
2. Lower the priority of issues you find cheap duplicates of elsewhere
3. Use the Wish List alongside `/collection/missing/<series_id>/` to cross-reference what you still need

## Status Workflow

Each wish list item moves through three statuses:

| Status | Meaning |
|--------|---------|
| **Wanted** | You are actively looking for this issue |
| **Found** | You have located a copy but have not purchased it yet |
| **Acquired** | You have purchased it (item also added to your collection) |

You can update the status manually using the edit button, or use the **Acquire** action (shopping cart icon) which records purchase details and creates a collection item in one step.

### Acquiring an Item

Click the shopping cart icon next to any item that is not yet acquired:

1. Optionally enter purchase details:
    - **Purchase Date**
    - **Price Paid**
    - **Store/Vendor**
    - **Notes**
2. Click **Mark as Acquired**

The item's status is set to Acquired and a new entry is created in your collection using the Minimum Grade you specified. If the issue is already in your collection, the collection item is left unchanged.

## Priority System

Priorities range from 1 (highest urgency) to 5 (lowest):

| Priority | Suggested Use |
|----------|--------------|
| 1 | Key issues, first appearances — buy on sight |
| 2 | High-value issues you actively search for |
| 3 | Standard wants — pick up when priced right |
| 4 | Nice to have — grab if cheap |
| 5 | Low urgency — would not turn it down |

The wish list is always sorted by priority so your most important finds appear at the top.

## Grading and Price

### Minimum Grade

Set the lowest CGC grade you will accept for each issue. Leave blank if any condition is acceptable.

Common targets:

- **9.4–9.8**: High-grade collecting or slabs
- **8.0–9.2**: Display copies — tight but not slab-grade
- **6.0–7.5**: Reader copies — presentable but affordable
- **1.0–5.0**: Reading copies only — condition does not matter

### Maximum Price

Record the most you are willing to spend. This appears in the wish list table as a quick reference when negotiating at shops or conventions. Leave blank if you have no budget limit.

## URLs Quick Reference

| URL | Purpose | Login Required |
|-----|---------|----------------|
| `/wish-list/` | View your wish list and add items | Yes |
| `/wish-list/item/<id>/update/` | Edit a wish list item | Yes* |
| `/wish-list/item/<id>/delete/` | Remove an item from your wish list | Yes* |
| `/wish-list/item/<id>/acquire/` | Mark as acquired and add to collection | Yes* |

*Must be the owner of the wish list.

## Tips and Best Practices

1. **Keep priorities honest**: Reserve priority 1 for issues you would buy immediately regardless of price — it loses meaning if everything is priority 1
2. **Set realistic grades**: A minimum grade of 9.8 on a 1960s book will keep it on your list forever; set grades appropriate to the era and your collecting goals
3. **Use maximum price as a floor**: Sellers at conventions will often meet you at your stated limit — knowing your number prevents impulse overpaying
4. **Review after conventions**: After a show, clean up Found items that you decided not to buy — reset them to Wanted or remove them
5. **Combine with Pull List**: Use the [Pull List](../pull_list/README.md) for ongoing series and the Wish List for specific back issues you are hunting
6. **Acquire promptly**: When you buy an issue, mark it Acquired right away so your wish list stays accurate and your collection stays up to date

---

For API documentation, see the main [API README](../api/README.md).
