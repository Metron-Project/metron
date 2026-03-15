class RateLimitHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if hasattr(request, "_throttle_headers"):
            for header, value in request._throttle_headers.items():
                response[header] = value
        return response
