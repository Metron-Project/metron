"""heggra's URLs, with a per-user limit on uploads.

heggra stores each upload as soon as it's picked, before its form is saved, and keeps it until
heggra_cleanup, run hourly, deletes it a little over a day later (HEGGRA_MAX_AGE plus an hour).
Without a limit, any logged-in account could fill storage by posting to the upload view
directly. Counted in the cache within a fixed window, so like the login limits (see
users.login_throttle) it fails open while Redis is unavailable.
"""

import contextlib

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


def _reserve(user) -> int:
    """Take one of ``user``'s uploads for the current window and return how many are taken.

    incr() is atomic, so requests sent at the same time each get their own count and can't all
    slip in under the limit.
    """
    key = _key(user)
    # The window starts at the first upload; add() is a no-op once it exists.
    cache.add(key, 0, timeout=UPLOAD_WINDOW)
    try:
        return cache.incr(key)
    except ValueError:
        # Expired between add() and incr(); start a fresh window.
        cache.add(key, 1, timeout=UPLOAD_WINDOW)
        return 1


def _release(user) -> None:
    """Give back an upload taken by _reserve() that wasn't saved."""
    # A window that expired in the meantime has nothing to give back.
    with contextlib.suppress(ValueError):
        cache.decr(_key(user))


@never_cache
@require_POST
def upload(request: HttpRequest) -> HttpResponse:
    """Refuse an upload once its user is over the limit, otherwise hand it to heggra.

    Only uploads heggra saved count, so files it refused, such as ones too large or not images,
    don't use up the user's allowance.
    """
    user = request.user
    # Anonymous requests are left to heggra, which refuses them itself.
    limited = user.is_authenticated and not user.is_staff
    if limited and _reserve(user) > UPLOAD_LIMIT:
        _release(user)
        context = {
            "classes": getattr(settings, "HEGGRA_CLASSES", {}),
            "messages": [_("You've uploaded too many files. Please try again in an hour.")],
        }
        response = render(request, "heggra/error.html", context, status=429)
        # heggra.js shows a response with this header in the widget, as it does heggra's errors.
        response.headers["X-Heggra-Error"] = "true"
        return response
    try:
        response = heggra_views.upload(request)
    except Exception:
        if limited:
            _release(user)
        raise
    # heggra sets this header only on an upload it saved.
    if limited and not response.headers.get("X-Heggra-Upload"):
        _release(user)
    return response


app_name = "heggra"

urlpatterns = [
    path("upload/", upload, name="upload"),
    path("preview/<str:token>/", heggra_views.preview, name="preview"),
]
