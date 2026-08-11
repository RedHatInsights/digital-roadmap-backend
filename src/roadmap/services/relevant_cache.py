import copy
import threading
import time
import typing as t


class RelevantResponseCache:
    """Simple in-memory TTL cache for relevant endpoint responses."""

    def __init__(self):
        self._entries: dict[tuple[t.Any, ...], tuple[float, t.Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: tuple[t.Any, ...]) -> t.Any | None:
        now = time.monotonic()
        with self._lock:
            item = self._entries.get(key)
            if item is None:
                return None

            expires_at, value = item
            if now >= expires_at:
                self._entries.pop(key, None)
                return None

            # Never return shared mutable references.
            return copy.deepcopy(value)

    def set(self, key: tuple[t.Any, ...], value: t.Any, ttl_seconds: int, maxsize: int):
        now = time.monotonic()
        with self._lock:
            if len(self._entries) >= maxsize:
                # Remove expired entries first, then oldest expiry if still full.
                expired = [k for k, (expires_at, _v) in self._entries.items() if now >= expires_at]
                for expired_key in expired:
                    self._entries.pop(expired_key, None)

                if len(self._entries) >= maxsize and self._entries:
                    oldest_key = min(self._entries.items(), key=lambda item: item[1][0])[0]
                    self._entries.pop(oldest_key, None)

            self._entries[key] = (now + ttl_seconds, copy.deepcopy(value))


def normalize_host_groups(host_groups: set[str | None] | None) -> tuple[str, ...]:
    """Return stable host-group key parts for cache scoping."""
    if not host_groups:
        return ()

    normalized = []
    for group_id in host_groups:
        normalized.append("__ungrouped__" if group_id is None else group_id)
    return tuple(sorted(normalized))


def build_relevant_cache_key(
    endpoint: str,
    org_id: str,
    related: bool,
    host_groups: set[str | None] | None,
    major: int | None = None,
    minor: int | None = None,
) -> tuple[t.Any, ...] | None:
    """Build cache key with tenant and permission scoping."""
    if not org_id:
        # Never cache identity-less responses to avoid accidental cross-user reuse.
        return None

    return (
        endpoint,
        org_id,
        related,
        major,
        minor,
        normalize_host_groups(host_groups),
    )


relevant_response_cache = RelevantResponseCache()


class CachedResult:
    """Wrap row mappings with AsyncResult-like iteration helpers."""

    def __init__(self, rows: list[t.Any]):
        self._rows = rows

    def yield_per(self, _n: int):
        return self

    def mappings(self):
        return self

    def __aiter__(self):
        return self._async_iter()

    async def _async_iter(self):
        for row in self._rows:
            yield row
