from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import PermissionDenied

from users import login_throttle


class RateLimitedModelBackend(ModelBackend):
    """ModelBackend that refuses logins after too many failures (see users.login_throttle).

    Covers every path that calls authenticate() with a request: the site, admin and
    browsable-API login forms, and DRF Basic auth. Calls without a request (e.g. the
    test client's login()) can't be attributed to an IP and aren't limited.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(get_user_model().USERNAME_FIELD)
        if request is None or username is None or password is None:
            return super().authenticate(request, username, password, **kwargs)

        if login_throttle.is_locked(request, username):
            setattr(request, login_throttle.LOCKED_REQUEST_ATTR, True)
            # PermissionDenied stops authenticate() trying any other backend.
            raise PermissionDenied(login_throttle.LOCKED_MESSAGE)

        user = super().authenticate(request, username, password, **kwargs)
        if user is None:
            login_throttle.record_failure(request, username)
        else:
            login_throttle.record_success(request, username)
        return user
