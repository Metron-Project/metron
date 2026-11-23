"""heggra's URLs, with a per-user limit on uploads.

heggra stores each upload as soon as it's picked, before its form is saved, and keeps it until
heggra_cleanup deletes it a day later. Without a limit, any logged-in account could fill storage
by posting to the upload view directly. Counted in the cache within a fixed window, so like the
login limits (see users.login_throttle) it fails open while Redis is unavailable.
"""

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import path
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from heggra import views as heggra_views

UPLOAD_WINDOW = 60 * 60  # seconds
# Enough for a contributor adding a week's covers in one sitting.
UPLOAD_LIMIT = 100
KEY_PREFIX = "heggra_upload"


def _count_upload(user) -> int:
    """Count an upload by ``user`` and return how many they've made in the current window."""
    key = f"{KEY_PREFIX}:{user.pk}"
    # The window starts at the first upload; add() is a no-op once it exists.
    cache.add(key, 0, timeout=UPLOAD_WINDOW)
    try:
        return cache.incr(key)
    except ValueError:
        # Expired between add() and incr(); start a fresh window.
        cache.add(key, 1, timeout=UPLOAD_WINDOW)
        return 1


@never_cache
@require_POST
def upload(request: HttpRequest) -> HttpResponse:
    """Refuse an upload once its user is over the limit, otherwise hand it to heggra."""
    user = request.user
    # Anonymous requests are left to heggra, which refuses them itself.
    if user.is_authenticated and not user.is_staff and _count_upload(user) > UPLOAD_LIMIT:
        context = {
            "classes": getattr(settings, "HEGGRA_CLASSES", {}),
            "messages": [_("You've uploaded too many files. Please try again in an hour.")],
        }
        response = render(request, "heggra/error.html", context, status=429)
        # heggra.js shows a response with this header in the widget, as it does heggra's errors.
        response.headers["X-Heggra-Error"] = "true"
        return response
    return heggra_views.upload(request)


app_name = "heggra"

urlpatterns = [
    path("upload/", upload, name="upload"),
    path("preview/<str:token>/", heggra_views.preview, name="preview"),
]
