import random
import time
from collections import defaultdict

from django.core.cache import cache
from django.core.management.base import BaseCommand

_DETAIL_PREFIX = "api:detail:"
_LIST_PREFIX = "api:list:"
_VERSION_PREFIX = "cachever:"
_BYTES_PER_UNIT = 1024


class Command(BaseCommand):
    help = (
        "One-off audit of the Redis-backed API response cache -- key counts and "
        "estimated memory footprint per category (api:detail:<model>, "
        "api:list:<model>, cachever, everything else), plus global hit-rate and "
        "eviction stats. Meant to be run against production shortly after the "
        "caching PR deploys (and again later) to see whether DETAIL_CACHE_TTL/"
        "LIST_CACHE_TTL (api/cache.py) need tuning, rather than guessing."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--sample-size",
            type=int,
            default=300,
            help=(
                "Max keys to sample per category for MEMORY USAGE, so the "
                "estimate doesn't require calling it on every key in a large "
                "keyspace (default: 300)"
            ),
        )
        parser.add_argument(
            "--scan-count",
            type=int,
            default=1000,
            help="COUNT hint passed to Redis SCAN per iteration (default: 1000)",
        )

    def handle(self, *args, **options) -> None:
        # Django's generic cache API has no SCAN/MEMORY USAGE/INFO -- those
        # require the raw redis-py client the RedisCache backend wraps.
        client = cache._cache.get_client()

        self._print_global_stats(client)
        categories, total_keys, elapsed = self._scan_and_categorize(client, options["scan_count"])
        self.stdout.write(f"\nScanned {total_keys:,} keys in {elapsed:.1f}s.")
        self._print_category_report(client, categories, options["sample_size"])

    def _print_global_stats(self, client) -> None:
        try:
            memory = client.info("memory")
            stats = client.info("stats")
        except Exception as exc:  # noqa: BLE001 -- best-effort diagnostics
            self.stdout.write(
                self.style.WARNING(f"INFO command unavailable ({exc}); skipping global stats.")
            )
            return

        hits = stats.get("keyspace_hits", 0)
        misses = stats.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = f"{hits / total:.1%}" if total else "n/a"

        self.stdout.write(
            self.style.MIGRATE_HEADING("Redis instance (global -- all keys, not just ours)")
        )
        self.stdout.write(f"  used_memory:       {memory.get('used_memory_human', '?')}")
        maxmemory = memory.get("maxmemory", 0)
        unbounded = "  (unbounded -- no eviction policy in effect)" if not maxmemory else ""
        self.stdout.write(f"  maxmemory:         {memory.get('maxmemory_human', '?')}{unbounded}")
        self.stdout.write(f"  maxmemory_policy:  {memory.get('maxmemory_policy', '?')}")
        self.stdout.write(f"  mem_fragmentation: {memory.get('mem_fragmentation_ratio', '?')}")
        self.stdout.write(f"  keyspace hit rate: {hit_rate} ({hits:,} hits / {misses:,} misses)")

        evicted = stats.get("evicted_keys", 0)
        evicted_line = f"  evicted_keys:      {evicted:,}"
        if evicted:
            evicted_line = self.style.WARNING(
                f"{evicted_line}  <-- Redis is evicting under memory pressure; "
                "TTLs alone aren't controlling memory here, lower them or add memory"
            )
        self.stdout.write(evicted_line)

    def _scan_and_categorize(self, client, scan_count: int):
        categories: dict[str, list[bytes]] = defaultdict(list)
        total_keys = 0
        cursor = 0
        start = time.monotonic()
        while True:
            cursor, keys = client.scan(cursor=cursor, count=scan_count)
            for raw_key in keys:
                total_keys += 1
                key = raw_key.decode() if isinstance(raw_key, bytes) else raw_key
                categories[self._categorize(key)].append(raw_key)
            if cursor == 0:
                break
        return categories, total_keys, time.monotonic() - start

    @staticmethod
    def _categorize(key: str) -> str:
        # Substring match rather than startswith(): robust to however Django's
        # RedisCache backend wraps the logical key (e.g. a ":<version>:"
        # prefix), without needing to know its exact format.
        if _DETAIL_PREFIX in key:
            model = key.split(_DETAIL_PREFIX, 1)[1].split(":", 1)[0]
            return f"api:detail:{model}"
        if _LIST_PREFIX in key:
            model = key.split(_LIST_PREFIX, 1)[1].split(":", 1)[0]
            return f"api:list:{model}"
        if _VERSION_PREFIX in key:
            return "cachever"
        return "other (Select2, throttling, etc.)"

    def _print_category_report(self, client, categories: dict, sample_size: int) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("\nBy category"))
        if not categories:
            self.stdout.write("  No keys found.")
            return

        rows = []
        for label, keys in categories.items():
            count = len(keys)
            avg_bytes = self._sample_avg_memory(client, keys, sample_size)
            est_total = avg_bytes * count if avg_bytes is not None else None
            rows.append((label, count, avg_bytes, est_total))
        rows.sort(key=lambda row: row[3] or 0, reverse=True)

        for label, count, avg_bytes, est_total in rows:
            avg_str = f"~{avg_bytes:,.0f} B/key" if avg_bytes is not None else "n/a"
            total_str = self._human_bytes(est_total)
            self.stdout.write(f"  {label:<32} {count:>8,} keys   {avg_str:>14}   est. {total_str}")

        known = sum(est for *_ignored, est in rows if est is not None)
        self.stdout.write(
            f"\n  Estimated total across sampled categories: {self._human_bytes(known)}"
        )
        self.stdout.write(
            "  (Estimates extrapolate from a random sample's MEMORY USAGE -- "
            "re-run periodically and compare, not just once.)"
        )

    @staticmethod
    def _sample_avg_memory(client, keys: list, sample_size: int) -> float | None:
        sample = keys if len(keys) <= sample_size else random.sample(keys, sample_size)
        sizes = []
        for key in sample:
            try:
                size = client.memory_usage(key)
            except Exception:  # noqa: BLE001, S112 -- best-effort; key may have expired mid-scan
                continue
            if size is not None:
                sizes.append(size)
        return sum(sizes) / len(sizes) if sizes else None

    @staticmethod
    def _human_bytes(n: float | None) -> str:
        if n is None:
            return "n/a"
        for unit in ("B", "KB", "MB", "GB"):
            if n < _BYTES_PER_UNIT:
                return f"{n:,.1f} {unit}"
            n /= _BYTES_PER_UNIT
        return f"{n:,.1f} TB"
