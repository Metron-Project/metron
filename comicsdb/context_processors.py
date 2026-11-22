from comicsdb.models.announcement import Announcement
from comicsdb.views.constants import DETAIL_PAGINATE_BY


def announcement_context_processor(request):
    return {"active_announcements": Announcement.active_announcements()}


def detail_page_size_context_processor(request):
    """Expose the detail-page "load more" page size, so templates don't hardcode it."""
    return {"detail_page_size": DETAIL_PAGINATE_BY}
