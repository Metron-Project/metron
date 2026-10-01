from unittest.mock import MagicMock, patch

import pytest
from redis.exceptions import TimeoutError as RedisTimeoutError

from metron.cache_backends import FailOpenRedisCache


@pytest.fixture
def broken_cache():
    backend = FailOpenRedisCache("redis://localhost:6379/0", {})
    client = MagicMock()
    for method in (
        "add",
        "get",
        "set",
        "touch",
        "delete",
        "get_many",
        "has_key",
        "incr",
        "set_many",
        "delete_many",
    ):
        getattr(client, method).side_effect = RedisTimeoutError("Timeout reading from socket")
    with patch.object(FailOpenRedisCache, "_cache", client):
        yield backend


def test_reads_return_defaults(broken_cache):
    assert broken_cache.get("key") is None
    assert broken_cache.get("key", []) == []
    assert broken_cache.get_many(["a", "b"]) == {}
    assert broken_cache.has_key("key") is False


def test_writes_are_swallowed(broken_cache):
    broken_cache.set("key", "value")
    broken_cache.delete_many(["a", "b"])
    assert broken_cache.add("key", 1) is False
    assert broken_cache.touch("key") is False
    assert broken_cache.delete("key") is False
    assert broken_cache.incr("key") == 0
    assert broken_cache.set_many({"a": 1, "b": 2}) == ["a", "b"]


def test_failure_is_logged(broken_cache, caplog):
    broken_cache.get("key")
    assert "Redis cache get failed" in caplog.text
