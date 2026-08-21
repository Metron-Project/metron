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
from enum import StrEnum
from typing import Any

from django.core.cache import cache

DETAIL_CACHE_TTL = 60 * 60 * 24  # 24h safety net; live keys self-invalidate on write.
LIST_CACHE_TTL = 60 * 2  # 2min; bounds staleness from nested-object changes we don't chase.

_VERSION_KEY_PREFIX = "cachever"


class ModelLabel(StrEnum):
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


def detail_cache_key(
    model_label: str, action: str, pk: Any, modified, *dependent_labels: str
) -> str:
    """Cache key for a single object's serialized detail response.

    Self-invalidating: a change to `modified` produces a new key, so old
    entries are simply orphaned and expire via TTL.

    `action` (e.g. "retrieve", "issue_list") distinguishes different
    endpoints hanging off the same object -- without it, retrieve and a
    detail-scoped action like issue_list produce the exact same key
    whenever their dependent_labels happen to match (the common case: both
    default to no dependent labels), so whichever response was cached first
    gets served back for the other, wrong shape and all.

    `dependent_labels` (optional) mix in other models' version counters, for
    responses that embed data from a related object whose own edits don't
    cascade a `modified` bump onto this one (e.g. a Series response embeds
    its Publisher's name, but renaming the Publisher doesn't touch the
    Series row).
    """
    key = f"api:detail:{model_label}:{action}:{pk}:{modified.timestamp()}"
    if dependent_labels:
        version_map = get_model_versions(dependent_labels)
        versions = "-".join(str(version_map[lbl]) for lbl in dependent_labels)
        key = f"{key}:{versions}"
    return key


def get_model_version(model_label: str) -> int:
    """Return the current cache-generation counter for a model, initializing
    it to 1 on first use."""
    key = f"{_VERSION_KEY_PREFIX}:{model_label}"
    version = cache.get(key)
    if version is not None:
        return version
    if cache.add(key, 1, timeout=None):
        return 1
    # Lost the initialization race to another caller -- read back what they set.
    return cache.get(key) or 1


def get_model_versions(model_labels: Iterable[str]) -> dict[str, int]:
    """Batch form of get_model_version(): one Redis round trip (get_many)
    for the common case where every counter already exists, instead of one
    round trip per label."""
    labels = list(dict.fromkeys(model_labels))  # de-dupe, preserve order
    keys = {lbl: f"{_VERSION_KEY_PREFIX}:{lbl}" for lbl in labels}
    cached = cache.get_many(keys.values())
    return {
        lbl: cached[key] if key in cached else get_model_version(lbl) for lbl, key in keys.items()
    }


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
    labels = (model_label, *dependent_labels)
    version_map = get_model_versions(labels)
    versions = "-".join(str(version_map[lbl]) for lbl in labels)
    normalized = "&".join(f"{k}={v}" for k, v in sorted(query))
    digest = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"api:list:{model_label}:{scope}:{versions}:{digest}"
