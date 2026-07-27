import base64
import logging
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.urls import reverse
from knox.auth import TokenAuthentication
from rest_framework import status
from rest_framework.authentication import (
    BaseAuthentication,
    BasicAuthentication,
    SessionAuthentication,
)

from api.authentication import record_auth_method_usage

TODAY = datetime.now(UTC).date().isoformat()


class DummyUser:
    username = "dummy"


class DummyRequest:
    def __init__(self, authenticator=None):
        self.successful_authenticator = authenticator


class _UnrecognizedAuthenticator(BaseAuthentication):
    """A real authenticator that isn't Basic/Session/Token, for the "other" case."""


# ---------------------------------------------------------------------------
# Unit tests — isolated from the real (shared) cache backend, since these
# counters are global-per-day and would otherwise collide with other tests
# running concurrently under pytest-xdist.
# ---------------------------------------------------------------------------


@pytest.fixture
def local_cache():
    # LocMemCache's backing store is a process-wide dict keyed by location, so a
    # fixed name would leak state between tests in the same xdist worker.
    test_cache = LocMemCache(f"test-auth-method-tracking-{uuid.uuid4()}", {})
    with patch("api.authentication.cache", test_cache):
        yield test_cache


def test_noop_when_no_successful_authenticator(local_cache):
    record_auth_method_usage(DummyRequest(authenticator=None), DummyUser())
    assert local_cache.get(f"authmethod:basic:{TODAY}") is None
    assert local_cache.get(f"authmethod:other:{TODAY}") is None


@pytest.mark.parametrize(
    ("authenticator_cls", "slug"),
    [
        (BasicAuthentication, "basic"),
        (SessionAuthentication, "session"),
        (TokenAuthentication, "token"),
        (_UnrecognizedAuthenticator, "other"),
    ],
)
def test_increments_counter_for_authenticator(local_cache, authenticator_cls, slug):
    record_auth_method_usage(DummyRequest(authenticator_cls()), DummyUser())
    assert local_cache.get(f"authmethod:{slug}:{TODAY}") == 1


def test_repeated_calls_increment_the_same_counter(local_cache):
    request = DummyRequest(TokenAuthentication())
    user = DummyUser()
    record_auth_method_usage(request, user)
    record_auth_method_usage(request, user)
    record_auth_method_usage(request, user)
    assert local_cache.get(f"authmethod:token:{TODAY}") == 3


def test_logs_username_and_auth_method(local_cache, caplog):
    caplog.set_level(logging.INFO, logger="api.authentication")
    record_auth_method_usage(DummyRequest(TokenAuthentication()), DummyUser())
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.username == "dummy"
    assert record.auth_method == "token"


# ---------------------------------------------------------------------------
# Integration tests — verify real requests trigger tracking with the right
# authenticator, without touching the shared cache (mocked out for the same
# reason as above).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_basic_auth_request_tracked_as_basic(create_user, api_client, test_password):
    user = create_user()
    credentials = base64.b64encode(f"{user.username}:{test_password}".encode()).decode()
    api_client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

    with patch("api.throttle.record_auth_method_usage") as mock_record:
        resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    mock_record.assert_called_once()
    called_request, called_user = mock_record.call_args.args
    assert called_user == user
    assert isinstance(called_request.successful_authenticator, BasicAuthentication)


@pytest.mark.django_db
def test_token_auth_request_tracked_as_token(api_client_with_token_credentials):
    api_client, user = api_client_with_token_credentials

    with patch("api.throttle.record_auth_method_usage") as mock_record:
        resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    mock_record.assert_called_once()
    called_request, called_user = mock_record.call_args.args
    assert called_user == user
    assert called_request.successful_authenticator.__class__.__name__ == "TokenAuthentication"


@pytest.mark.django_db
def test_session_auth_request_tracked_as_session(create_user, api_client, test_password):
    user = create_user()
    api_client.login(username=user.username, password=test_password)

    with patch("api.throttle.record_auth_method_usage") as mock_record:
        resp = api_client.get(reverse("api:arc-list"))

    assert resp.status_code == status.HTTP_200_OK
    mock_record.assert_called_once()
    called_request, called_user = mock_record.call_args.args
    assert called_user == user
    assert called_request.successful_authenticator.__class__.__name__ == "SessionAuthentication"
