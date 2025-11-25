# Reading Lists - User Guide

The Reading Lists feature allows you to create, manage, and share curated comic book reading lists. These lists help organize issues into logical reading orders, whether for story arcs, crossover events, or custom collections.

## Table of Contents

- [Features](#features)
- [Getting Started](#getting-started)
- [Usage Examples](#usage-examples)
- [Search and Autocomplete](#search-and-autocomplete)
- [Permissions and Privacy](#permissions-and-privacy)

## Features

### Core Functionality

- **Create Reading Lists**: Build your own custom reading orders
- **Public/Private Lists**: Share your lists with the community or keep them private
- **Drag-and-Drop Ordering**: Easily reorder issues within your lists
- **Smart Search**: Find issues quickly using autocomplete with series and issue number filters
- **Attribution Tracking**: Credit sources for reading orders (admin feature)

### Automatic Information

Reading lists automatically display:
- **Start Year**: The earliest cover date year from issues in the list
- **End Year**: The latest cover date year from issues in the list
- **Publishers**: All unique publishers represented in the list

## Getting Started

### Viewing Reading Lists

**Browse All Lists**
- Visit `/reading-lists/` to see all public reading lists
- If you're logged in, you'll also see your own private lists

**Search for Lists**
- Use `/reading-lists/search/` to search by name, username, or source
- Example: Search "marvel" to find Marvel-related reading orders

**Your Lists**
- Visit `/reading-lists/my-lists/` to see only your reading lists (requires login)

### Creating Your First Reading List

1. Log in to your account
2. Navigate to `/reading-lists/create/`
3. Enter a name for your list (required)
4. Add a description (optional but recommended)
5. Choose whether to make it public or private
6. Click "Create"

## Usage Examples

### Creating a Reading List

1. Navigate to `/reading-lists/create/`
2. Enter a name (required)
3. Add a description (optional)
4. Choose public or private:
   - **Public**: Anyone can view your list
   - **Private**: Only you can see it
5. Click "Create"

### Adding Issues to Your List

You have two methods to add issues to your reading list:

#### Method 1: Add Individual Issues (Search & Select)

1. View your reading list detail page
2. Click "Add Issues"
3. Search for issues using the autocomplete field (see [Search Tips](#search-and-autocomplete))
4. Selected issues appear in the list below
5. Drag and drop to reorder both new and existing issues
6. Click "Submit" to save your changes

**Tips:**
- You can add multiple issues at once
- Drag and drop works for both new issues you're adding and existing issues in your list
- The system will skip any duplicate issues automatically

#### Method 2: Add from Series (Bulk Addition)

Perfect for creating large reading lists quickly!

1. View your reading list detail page
2. Click "Add from Series"
3. Search and select a series
4. Choose what to add:
   - **All issues**: Adds every issue from the series
   - **Issue range**: Specify start and/or end issue numbers
     - Example: Start at #1, end at #50 (adds issues 1-50)
     - Example: Start at #10 (adds issue 10 through the end)
     - Example: End at #25 (adds beginning through issue 25)
5. Choose position: Add at beginning or end of your list
6. Click "Add Issues"

**Benefits:**
- Quickly add entire series runs (100+ issues in seconds)
- Issues added in chronological order by cover date
- Automatically skips duplicates
- Perfect for event reading orders spanning multiple series

### Editing a Reading List

1. Navigate to your reading list detail page
2. Click "Edit" (or "Update")
3. Modify the name, description, or privacy setting
4. Click "Update" to save changes

### Removing Issues

1. View your reading list detail page
2. Find the issue you want to remove
3. Click the "Remove" button next to the issue
4. Confirm the removal

### Deleting a Reading List

1. Navigate to your reading list detail page
2. Click "Delete"
3. Confirm the deletion
4. The list and all its issue associations will be permanently removed

## Search and Autocomplete

### Searching for Reading Lists

The search functionality allows you to find lists by:
- **List name** (case-insensitive)
- **Username** of the list owner
- **Attribution source** (e.g., "Comic Book Reading Orders")

**Example:** Searching "marvel" would find:
- Lists with "marvel" in the name
- Lists created by user "marvelFan"
- Lists from "Complete Marvel Reading Orders" (CMRO)

### Searching for Issues

When adding issues to your reading list, you can use smart search:

**Basic Search:**
- Type any text to search both series names and issue numbers
- Example: Type `"spider"` to find all Spider-Man series

**Smart Search with #:**
Use the `#` symbol to separate series name from issue number for more precise results.

**Format:** `series name #issue number`

**Examples:**
- `"spider #1"` → Spider-Man series, issue #1
- `"amazing #700"` → Amazing Spider-Man, issue #700
- `"#100"` → All series, issue #100
- `"x-men #1"` → X-Men series, issue #1
- `"avengers"` → All Avengers series (any issue number)

**Tips:**
- Search is case-insensitive
- Partial matches work for series names
- You can search by just series name or just issue number

## Permissions and Privacy

### What You Can Do

**As a Regular User:**
- Create unlimited reading lists
- Edit and delete your own lists
- Add and remove issues from your lists
- View all public lists
- View your own private lists

**Privacy Settings:**
- **Public Lists**: Visible to everyone (logged in or not)
- **Private Lists**: Only visible to you when logged in

### What You Cannot Do

- Edit or delete other users' reading lists
- View other users' private lists
- Set attribution sources (admin only)

### Admin Features

Admin users have additional capabilities:
- Can set attribution sources and URLs
- Can manage lists owned by the "Metron" user
- Can view Metron's private lists

### Metron User Lists

Some reading lists are owned by a special "Metron" user account:
- They represent curated/official reading orders
- Admin users can manage these lists
- Public Metron lists are visible to everyone

## URLs Quick Reference

| URL | Purpose | Login Required |
|-----|---------|----------------|
| `/reading-lists/` | Browse all public lists | No |
| `/reading-lists/search/` | Search reading lists | No |
| `/reading-lists/<slug>/` | View a specific list | No* |
| `/reading-lists/my-lists/` | View your lists | Yes |
| `/reading-lists/create/` | Create a new list | Yes |
| `/reading-lists/<slug>/update/` | Edit your list | Yes |
| `/reading-lists/<slug>/delete/` | Delete your list | Yes |
| `/reading-lists/<slug>/add-issue/` | Add issues individually | Yes |
| `/reading-lists/<slug>/add-from-series/` | Add issues from series (bulk) | Yes |

*Unauthenticated users can only view public lists.

## Tips and Best Practices

### Creating Great Reading Lists

1. **Use descriptive names**: "Secret Wars (2015)" is better than "My List"
2. **Add descriptions**: Explain what the reading order covers
3. **Credit your sources**: If you got the order from a website, note it in the description
4. **Consider privacy**: Make lists public to share with the community
5. **Keep it organized**: Use drag-and-drop to ensure proper reading order

### Managing Large Lists

1. **Use "Add from Series"**: For reading lists with 100+ issues, use the bulk addition feature
2. **Build incrementally**: Add one series at a time, then fine-tune the order
3. **Mix both methods**: Use bulk add for series runs, individual add for one-offs
4. **Search efficiently**: Use the `#` separator for precise searches when adding individual issues
5. **Review before saving**: Check the order in the preview before submitting
6. **Edit incrementally**: You can always add more issues later

**Example Workflow for Large Lists:**
1. Use "Add from Series" to add Amazing Spider-Man #1-50
2. Use "Add from Series" to add Avengers #1-30 at the end
3. Use "Add Issues" to insert specific tie-ins or crossovers
4. Drag and drop to adjust the final reading order

### Contributing to the Community

1. **Make quality lists public**: Share your research with others
2. **Use clear descriptions**: Help others understand the reading order
3. **Keep lists updated**: Return to add new issues as series continue
4. **Report issues**: If you find problems, contact an admin

---

For technical documentation and developer information, see [TECHNICAL.md](TECHNICAL.md).
