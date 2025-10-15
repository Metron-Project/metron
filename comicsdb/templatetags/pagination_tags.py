"""
Custom template tags for pagination functionality.
Place this file in: comicsdb/templatetags/pagination_tags.py
"""

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Preserves existing query parameters while updating/adding new ones.

    Usage:
        {% url_replace page=2 %}
        {% url_replace page=page_obj.next_page_number %}
    """
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return query.urlencode()


@register.simple_tag(takes_context=True)
def get_pagination_range(context, page_obj, paginator):
    """
    Returns a list of page numbers to display in pagination.
    Shows first page, last page, current page, and nearby pages with ellipsis.

    Returns a list that may contain integers (page numbers) or strings ('ellipsis').
    """
    current_page = page_obj.number
    total_pages = paginator.num_pages

    # Always show first and last page
    pages = []

    # Show pages around current page (within 2 pages)
    page_range = range(max(1, current_page - 2), min(total_pages + 1, current_page + 3))

    for page_num in range(1, total_pages + 1):
        if page_num == 1 or page_num == total_pages or page_num in page_range:  # noqa: PLR1714
            pages.append(page_num)
        elif pages and pages[-1] != "ellipsis":
            pages.append("ellipsis")

    return pages


@register.filter
def get_item(dictionary, key):
    """
    Gets an item from a dictionary using a variable key.

    Usage:
        {{ my_dict|get_item:key_variable }}
    """
    return dictionary.get(key)
