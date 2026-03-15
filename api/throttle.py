import math

from rest_framework.throttling import UserRateThrottle


class RateLimitHeadersMixin:
    def allow_request(self, request, view):
        result = super().allow_request(request, view)
        if hasattr(self, "num_requests") and self.num_requests is not None:
            django_request = request._request
            if not hasattr(django_request, "_throttle_headers"):
                django_request._throttle_headers = {}
            remaining = max(0, self.num_requests - len(self.history))
            if self.history:
                reset_time = math.ceil(self.history[-1] + self.duration)
            else:
                reset_time = math.ceil(self.now + self.duration)
            scope = getattr(self, "scope", "default").capitalize()
            django_request._throttle_headers[f"X-RateLimit-{scope}-Limit"] = str(self.num_requests)
            django_request._throttle_headers[f"X-RateLimit-{scope}-Remaining"] = str(remaining)
            django_request._throttle_headers[f"X-RateLimit-{scope}-Reset"] = str(reset_time)
        return result


class BurstRateThrottle(RateLimitHeadersMixin, UserRateThrottle):
    scope = "burst"


class SustainedRateThrottle(RateLimitHeadersMixin, UserRateThrottle):
    scope = "sustained"
