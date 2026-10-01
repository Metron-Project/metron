import logging

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.redis import RedisCache
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class FailOpenRedisCache(RedisCache):
    """RedisCache that treats Redis errors (timeouts, dropped connections) as cache misses.

    Everything we keep in Redis is disposable -- API response caching, throttle history,
    usage counters, Select2 data -- so a stalled or unreachable Redis should degrade to
    "no cache" rather than turning every request into a 500. Reads return the default,
    writes become no-ops, and a warning is logged.

    Side effect: while Redis is failing, DRF throttling can't read request history, so
    rate limits are not enforced until it recovers.
    """

    def _log_failure(self, operation, exc):
        logger.warning("Redis cache %s failed, treating as a miss: %r", operation, exc)

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            return super().add(key, value, timeout, version)
        except RedisError as exc:
            self._log_failure("add", exc)
            return False

    def get(self, key, default=None, version=None):
        try:
            return super().get(key, default, version)
        except RedisError as exc:
            self._log_failure("get", exc)
            return default

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            super().set(key, value, timeout, version)
        except RedisError as exc:
            self._log_failure("set", exc)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            return super().touch(key, timeout, version)
        except RedisError as exc:
            self._log_failure("touch", exc)
            return False

    def delete(self, key, version=None):
        try:
            return super().delete(key, version)
        except RedisError as exc:
            self._log_failure("delete", exc)
            return False

    def get_many(self, keys, version=None):
        try:
            return super().get_many(keys, version)
        except RedisError as exc:
            self._log_failure("get_many", exc)
            return {}

    def has_key(self, key, version=None):
        try:
            return super().has_key(key, version)
        except RedisError as exc:
            self._log_failure("has_key", exc)
            return False

    def incr(self, key, delta=1, version=None):
        try:
            return super().incr(key, delta, version)
        except RedisError as exc:
            self._log_failure("incr", exc)
            return 0

    def set_many(self, data, timeout=DEFAULT_TIMEOUT, version=None):
        try:
            return super().set_many(data, timeout, version)
        except RedisError as exc:
            self._log_failure("set_many", exc)
            return list(data)

    def delete_many(self, keys, version=None):
        try:
            super().delete_many(keys, version)
        except RedisError as exc:
            self._log_failure("delete_many", exc)
