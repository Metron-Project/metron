"""Redis-backed cache of each cacheable model's `modified` timestamp."""

import logging
from datetime import UTC, datetime

from django.core.cache import cache

LOGGER = logging.getLogger(__name__)

LAST_MODIFIED_CACHE_TTL = 60 * 60 * 24 * 30  # 30 days


def last_modified_cache_key(model, pk) -> str:
    return f"modified:{model._meta.label_lower}:{pk}"


def _safe_get(key):
    try:
        return cache.get(key)
    except Exception:  # noqa: BLE001
        LOGGER.warning("Failed to read cache key %s", key, exc_info=True)
        return None


def _safe_set(key, value, timeout):
    try:
        cache.set(key, value, timeout)
    except Exception:  # noqa: BLE001
        LOGGER.warning("Failed to write cache key %s", key, exc_info=True)


def _safe_delete_many(keys):
    try:
        cache.delete_many(keys)
    except Exception:  # noqa: BLE001
        LOGGER.warning("Failed to delete cache keys %s", keys, exc_info=True)


def get_last_modified(model, pk) -> datetime | None:
    """Cached `modified` for `model`/`pk`, or None on a miss."""
    value = _safe_get(last_modified_cache_key(model, pk))

    if not isinstance(value, int):
        return None

    return datetime.fromtimestamp(value, tz=UTC)


def set_last_modified(instance) -> None:
    """Write-through cache update for a model instance."""
    modified = getattr(instance, "modified", None)

    if modified is None:
        return

    key = last_modified_cache_key(instance.__class__, instance.pk)
    _safe_set(key, int(modified.timestamp()), LAST_MODIFIED_CACHE_TTL)


def delete_last_modified(model, pk) -> None:
    _safe_delete_many([last_modified_cache_key(model, pk)])


def delete_last_modified_many(model, pks) -> None:
    _safe_delete_many([last_modified_cache_key(model, pk) for pk in pks])
