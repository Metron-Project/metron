from datetime import UTC, datetime
from unittest.mock import Mock, patch

from comicsdb.cache import (
    delete_last_modified,
    delete_last_modified_many,
    get_last_modified,
    last_modified_cache_key,
    set_last_modified,
)
from comicsdb.models.arc import Arc
from comicsdb.models.character import Character


def _instance(model, pk, modified):
    instance = Mock(spec=["pk", "modified"])
    instance.__class__ = model
    instance.pk = pk
    instance.modified = modified
    return instance


def test_last_modified_cache_key_is_model_qualified():
    assert last_modified_cache_key(Arc, 42) == "modified:comicsdb.arc:42"


def test_arc_and_character_with_same_pk_do_not_collide():
    now = datetime(2024, 1, 1, tzinfo=UTC)
    set_last_modified(_instance(Arc, 1, now))

    assert get_last_modified(Character, 1) is None
    assert get_last_modified(Arc, 1) == now


def test_get_last_modified_round_trips():
    now = datetime(2024, 6, 15, 12, 30, tzinfo=UTC)
    set_last_modified(_instance(Arc, 7, now))

    assert get_last_modified(Arc, 7) == now


def test_get_last_modified_missing_key_returns_none():
    assert get_last_modified(Arc, 999) is None


def test_set_last_modified_noop_without_modified():
    set_last_modified(_instance(Arc, 5, None))

    assert get_last_modified(Arc, 5) is None


def test_delete_last_modified():
    set_last_modified(_instance(Arc, 3, datetime.now(tz=UTC)))
    delete_last_modified(Arc, 3)

    assert get_last_modified(Arc, 3) is None


def test_delete_last_modified_many():
    now = datetime.now(tz=UTC)
    set_last_modified(_instance(Arc, 1, now))
    set_last_modified(_instance(Arc, 2, now))

    delete_last_modified_many(Arc, [1, 2])

    assert get_last_modified(Arc, 1) is None
    assert get_last_modified(Arc, 2) is None


def test_read_failure_degrades_to_none():
    with patch("comicsdb.cache.cache") as mock_cache:
        mock_cache.get.side_effect = Exception("redis down")
        assert get_last_modified(Arc, 1) is None


def test_write_failure_does_not_raise():
    with patch("comicsdb.cache.cache") as mock_cache:
        mock_cache.set.side_effect = Exception("redis down")
        set_last_modified(_instance(Arc, 1, datetime.now(tz=UTC)))


def test_delete_failure_does_not_raise():
    with patch("comicsdb.cache.cache") as mock_cache:
        mock_cache.delete_many.side_effect = Exception("redis down")
        delete_last_modified(Arc, 1)
