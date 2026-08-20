"""Redis-backed response caching for the read-only DRF API.

Two independent invalidation schemes are used, depending on endpoint shape:

* Detail responses (retrieve, and detail-scoped actions like issue_list) are
  cached under a self-versioning key derived from the object's ``modified``
  timestamp -- when ``modified`` changes, the key changes with it, so old
  entries are simply orphaned and expire via TTL. No explicit invalidation
  is needed.
* List responses (list, and collection-scoped actions like series_list) are
  cached under a key that includes a per-model cache-generation counter in
  Redis, bumped by signal handlers (see comicsdb/signals.py) whenever data a
  list response could embed changes.
"""

import hashlib
from collections.abc import Iterable
from typing import Any

from django.core.cache import cache

DETAIL_CACHE_TTL = 60 * 60 * 24  # 24h safety net; live keys self-invalidate on write.
LIST_CACHE_TTL = 60 * 2  # 2min; bounds staleness from nested-object changes we don't chase.

_VERSION_KEY_PREFIX = "cachever"


class ModelLabel:
    """Stable cache-key labels shared between signal handlers and views."""

    ARC = "arc"
    CHARACTER = "character"
    CREATOR = "creator"
    IMPRINT = "imprint"
    ISSUE = "issue"
    PUBLISHER = "publisher"
    SERIES = "series"
    TEAM = "team"
    UNIVERSE = "universe"


def detail_cache_key(model_label: str, pk: Any, modified) -> str:
    """Cache key for a single object's serialized detail response.

    Self-invalidating: a change to `modified` produces a new key, so old
    entries are simply orphaned and expire via TTL.
    """
    return f"api:detail:{model_label}:{pk}:{modified.timestamp()}"


def get_model_version(model_label: str) -> int:
    """Return the current cache-generation counter for a model, initializing
    it to 1 on first use."""
    key = f"{_VERSION_KEY_PREFIX}:{model_label}"
    version = cache.get(key)
    if version is None:
        cache.add(key, 1, timeout=None)
        version = cache.get(key) or 1
    return version


def bump_model_version(model_label: str) -> None:
    """Invalidate list caches that depend on `model_label` by advancing its
    generation counter."""
    key = f"{_VERSION_KEY_PREFIX}:{model_label}"
    try:
        cache.incr(key)
    except ValueError:
        # Key doesn't exist yet. At most one concurrent caller's `add` wins;
        # the other's bump is harmlessly absorbed, since a version key that
        # didn't exist means no list cache entry was ever computed under any
        # version of it either.
        cache.add(key, 1, timeout=None)


def list_cache_key(
    model_label: str,
    *dependent_labels: str,
    query: Iterable[tuple[str, list[str]]],
    scope: str = "",
) -> str:
    """Cache key for a list-type response: one or more model versions plus a
    normalized hash of the request's query params.

    `query` should come from `request.query_params.lists()` (multi-value),
    not `.dict()` -- `.dict()` silently drops all-but-the-last value for
    repeated params (e.g. IssueFilter's `role_id`), which would let distinct
    multi-value requests collide on the same key.
    """
    versions = "-".join(str(get_model_version(lbl)) for lbl in (model_label, *dependent_labels))
    normalized = "&".join(f"{k}={v}" for k, v in sorted(query))
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"api:list:{model_label}:{scope}:{versions}:{digest}"
