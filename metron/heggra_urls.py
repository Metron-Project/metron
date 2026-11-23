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


def _key(user) -> str:
    return f"{KEY_PREFIX}:{user.pk}"


def _count_upload(user) -> None:
    """Count an upload that ``user`` saved to temporary storage."""
    key = _key(user)
    # The window starts at the first upload; add() is a no-op once it exists.
    cache.add(key, 0, timeout=UPLOAD_WINDOW)
    try:
        cache.incr(key)
    except ValueError:
        # Expired between add() and incr(); start a fresh window.
        cache.add(key, 1, timeout=UPLOAD_WINDOW)


@never_cache
@require_POST
def upload(request: HttpRequest) -> HttpResponse:
    """Refuse an upload once its user is at the limit, otherwise hand it to heggra.

    Only uploads heggra saved count, so files it refused, such as ones too large or not images,
    don't use up the user's allowance.
    """
    user = request.user
    # Anonymous requests are left to heggra, which refuses them itself.
    limited = user.is_authenticated and not user.is_staff
    if limited and cache.get(_key(user), 0) >= UPLOAD_LIMIT:
        context = {
            "classes": getattr(settings, "HEGGRA_CLASSES", {}),
            "messages": [_("You've uploaded too many files. Please try again in an hour.")],
        }
        response = render(request, "heggra/error.html", context, status=429)
        # heggra.js shows a response with this header in the widget, as it does heggra's errors.
        response.headers["X-Heggra-Error"] = "true"
        return response
    response = heggra_views.upload(request)
    # heggra sets this header only on an upload it saved.
    if limited and response.headers.get("X-Heggra-Upload"):
        _count_upload(user)
    return response


app_name = "heggra"

urlpatterns = [
    path("upload/", upload, name="upload"),
    path("preview/<str:token>/", heggra_views.preview, name="preview"),
]
