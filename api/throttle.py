import math

from rest_framework.throttling import UserRateThrottle

from api.authentication import record_auth_method_usage
from api.client_health import record_throttled_request


class RateLimitHeadersMixin:
    def _expiring_entry_index(self):
        """Return how many of the oldest history entries must expire to admit a request.

        Normally that is 1 (the history is exactly at the limit). It is larger when a
        user is above the limit, e.g. after the limit was lowered: history is only pruned
        by age and rejected requests add no entries, so the user stays blocked until
        enough old entries age out.
        """
        return max(1, len(self.history) - self.num_requests + 1)

    def wait(self):
        """Seconds until a request would be allowed again.

        DRF returns None when the user is over the limit, which drops the Retry-After
        header from the 429. Compute it from the entry that has to expire instead.
        """
        index = self._expiring_entry_index()
        if index == 1:
            return super().wait()
        return max(0, self.history[-index] + self.duration - self.now)

    def allow_request(self, request, view):
        result = super().allow_request(request, view)
        if hasattr(self, "num_requests") and self.num_requests is not None:
            django_request = request._request
            if not hasattr(django_request, "_throttle_headers"):
                django_request._throttle_headers = {}
            remaining = max(0, self.num_requests - len(self.history))
            if self.history:
                reset_time = math.ceil(self.history[-self._expiring_entry_index()] + self.duration)
            else:
                reset_time = math.ceil(self.now + self.duration)
            scope = getattr(self, "scope", "default").capitalize()
            django_request._throttle_headers[f"X-RateLimit-{scope}-Limit"] = str(self.num_requests)
            django_request._throttle_headers[f"X-RateLimit-{scope}-Remaining"] = str(remaining)
            django_request._throttle_headers[f"X-RateLimit-{scope}-Reset"] = str(reset_time)
        if not result:
            record_throttled_request(request, getattr(self, "scope", "default"))
        return result


class BurstRateThrottle(RateLimitHeadersMixin, UserRateThrottle):
    scope = "burst"


class SustainedRateThrottle(RateLimitHeadersMixin, UserRateThrottle):
    scope = "sustained"

    def allow_request(self, request, view):
        user = request.user
        if user and user.is_authenticated:
            supporter_limit = getattr(user, "supporter_daily_limit", None)
            if supporter_limit:
                self.num_requests, self.duration = self.parse_rate(f"{supporter_limit}/day")
            record_auth_method_usage(request, user)
        return super().allow_request(request, view)
