import io
import uuid
from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command

from api.management.commands.audit_response_cache import Command

COMMAND = "audit_response_cache"


def test_categorize_detail_key_extracts_model_label():
    key = ":1:api:detail:issue:42:1704085200.0"
    assert Command._categorize(key) == "api:detail:issue"


def test_categorize_detail_key_with_dependent_labels_still_extracts_model():
    key = ":1:api:detail:series:7:1704085200.0:12-3"
    assert Command._categorize(key) == "api:detail:series"


def test_categorize_list_key_extracts_model_label():
    key = ":1:api:list:arc::4-2:abcdef0123456789"
    assert Command._categorize(key) == "api:list:arc"


def test_categorize_cachever_key():
    assert Command._categorize(":1:cachever:issue") == "cachever"


def test_categorize_unrelated_key_falls_back_to_other():
    assert Command._categorize(":1:django_select2:some-widget-id") == (
        "other (Select2, throttling, etc.)"
    )


def test_human_bytes_formats_across_units():
    assert Command._human_bytes(512) == "512.0 B"
    assert Command._human_bytes(2048) == "2.0 KB"
    assert Command._human_bytes(5 * 1024 * 1024) == "5.0 MB"
    assert Command._human_bytes(None) == "n/a"


def test_report_counts_and_sizes_a_seeded_category():
    """Seed a handful of keys under a category unique to this test run (a
    random model label) so the assertion is immune to whatever other keys
    real Redis happens to hold -- other test workers/dev usage share this
    same Redis instance, and the command intentionally scans everything."""
    label = f"audit-test-{uuid.uuid4().hex[:8]}"
    keys = [f"api:detail:{label}:{i}:1704085200.0" for i in range(3)]
    for key in keys:
        cache.set(key, {"payload": "x" * 50}, 60)

    out = io.StringIO()
    try:
        call_command(COMMAND, stdout=out)
    finally:
        cache.delete_many(keys)

    output = out.getvalue()
    assert f"api:detail:{label}" in output
    assert "3 keys" in output
    assert "Redis instance (global" in output
    assert "By category" in output


def test_info_failure_is_reported_without_crashing():
    class _BrokenClient:
        def info(self, *_args, **_kwargs):
            raise ConnectionError("redis unavailable")

        def scan(self, cursor=0, **_kwargs):
            return 0, []

    with patch("django.core.cache.cache._cache.get_client", return_value=_BrokenClient()):
        out = io.StringIO()
        call_command(COMMAND, stdout=out)

    output = out.getvalue()
    assert "INFO command unavailable" in output
    assert "redis unavailable" in output
