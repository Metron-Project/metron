from django import template

register = template.Library()


@register.filter
def star_fill_percent(average_rating, star_num):
    """Fill percentage (0-100) for star position `star_num` (1-5) given an average rating."""
    if not average_rating:
        return 0
    fill = float(average_rating) - (int(star_num) - 1)
    return round(max(0.0, min(1.0, fill)) * 100)
