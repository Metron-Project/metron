import pytest
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse
from rest_framework import status

from api.middleware import RateLimitHeadersMiddleware

# ---------------------------------------------------------------------------
# Middleware unit tests (no database required)
# ---------------------------------------------------------------------------


def _make_middleware(response=None):
    if response is None:
        response = HttpResponse()
    return RateLimitHeadersMiddleware(get_response=lambda r: response), response


def test_middleware_adds_throttle_headers_to_response():
    request = RequestFactory().get("/")
    request._throttle_headers = {
        "X-RateLimit-Burst-Limit": "20",
        "X-RateLimit-Burst-Remaining": "19",
        "X-RateLimit-Burst-Reset": "1700000060",
    }
    middleware, _response = _make_middleware()
    result = middleware(request)
    assert result["X-RateLimit-Burst-Limit"] == "20"
    assert result["X-RateLimit-Burst-Remaining"] == "19"
    assert result["X-RateLimit-Burst-Reset"] == "1700000060"


def test_middleware_does_not_add_headers_when_none_set():
    request = RequestFactory().get("/")
    middleware, response = _make_middleware()
    middleware(request)
    assert "X-RateLimit-Burst-Limit" not in response
    assert "X-RateLimit-Sustained-Limit" not in response


# ---------------------------------------------------------------------------
# Integration tests — verify headers appear on real API responses
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_response_includes_burst_rate_limit_headers(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "X-RateLimit-Burst-Limit" in resp
    assert "X-RateLimit-Burst-Remaining" in resp
    assert "X-RateLimit-Burst-Reset" in resp


@pytest.mark.django_db
def test_response_includes_sustained_rate_limit_headers(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK
    assert "X-RateLimit-Sustained-Limit" in resp
    assert "X-RateLimit-Sustained-Remaining" in resp
    assert "X-RateLimit-Sustained-Reset" in resp


@pytest.mark.django_db
def test_rate_limit_header_values_are_integers(api_client_with_credentials):
    resp = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp.status_code == status.HTTP_200_OK
    for header in (
        "X-RateLimit-Burst-Limit",
        "X-RateLimit-Burst-Remaining",
        "X-RateLimit-Burst-Reset",
        "X-RateLimit-Sustained-Limit",
        "X-RateLimit-Sustained-Remaining",
        "X-RateLimit-Sustained-Reset",
    ):
        assert resp[header].isdigit(), f"{header} value {resp[header]!r} is not an integer"


@pytest.mark.django_db
def test_burst_remaining_decrements_on_successive_requests(api_client_with_credentials):
    resp1 = api_client_with_credentials.get(reverse("api:arc-list"))
    resp2 = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp1.status_code == status.HTTP_200_OK
    assert resp2.status_code == status.HTTP_200_OK
    remaining1 = int(resp1["X-RateLimit-Burst-Remaining"])
    remaining2 = int(resp2["X-RateLimit-Burst-Remaining"])
    assert remaining2 == remaining1 - 1


@pytest.mark.django_db
def test_sustained_remaining_decrements_on_successive_requests(api_client_with_credentials):
    resp1 = api_client_with_credentials.get(reverse("api:arc-list"))
    resp2 = api_client_with_credentials.get(reverse("api:arc-list"))
    assert resp1.status_code == status.HTTP_200_OK
    assert resp2.status_code == status.HTTP_200_OK
    remaining1 = int(resp1["X-RateLimit-Sustained-Remaining"])
    remaining2 = int(resp2["X-RateLimit-Sustained-Remaining"])
    assert remaining2 == remaining1 - 1
