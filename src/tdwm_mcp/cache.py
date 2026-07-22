"""
TTL micro-cache with single-flight coalescing for hot read tools.

Metadata-ish reads (workload lists, rulesets, config) are hammered by
dashboards and agents. A short TTL collapses repeated calls into cached
responses, and single-flight ensures N concurrent identical calls share ONE
database round trip instead of N.

The cache is per-process. TTLs are short (seconds), so multi-replica
deployments stay coherent enough for monitoring data.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger(__name__)

# Opportunistic purge threshold — the key space (tool x args) is tiny, this
# is just a safety bound.
_MAX_ENTRIES = 128


class _LeaderGone(Exception):
    """The in-flight leader was cancelled; followers should retry."""


class TTLCache:
    """Async TTL cache with single-flight request coalescing."""

    def __init__(self):
        self._data: dict[Any, tuple[float, Any]] = {}
        self._inflight: dict[Any, asyncio.Future] = {}

    async def get_or_compute(
        self,
        key: Any,
        factory: Callable[[], Awaitable[Any]],
        ttl: float,
        cacheable: Callable[[Any], bool] = lambda r: True,
        on_hit: Optional[Callable[[], None]] = None,
    ) -> Any:
        """Return a fresh cached value, join an in-flight computation, or
        compute (as leader) and share the result.

        A cancelled leader signals followers to retry rather than
        propagating its CancelledError into unrelated requests.
        """
        while True:
            entry = self._data.get(key)
            if entry and entry[0] > time.monotonic():
                if on_hit:
                    on_hit()
                return entry[1]

            fut = self._inflight.get(key)
            if fut is None:
                break  # no leader — become one
            try:
                result = await asyncio.shield(fut)
                if on_hit:
                    on_hit()
                return result
            except _LeaderGone:
                continue  # leader was cancelled; loop and retry

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        # Followers may never await this future; mark exceptions retrieved
        # so the event loop doesn't log "exception was never retrieved".
        fut.add_done_callback(
            lambda f: f.exception() if not f.cancelled() else None)
        self._inflight[key] = fut
        try:
            result = await factory()
        except asyncio.CancelledError:
            fut.set_exception(_LeaderGone())
            raise
        except BaseException as e:
            fut.set_exception(e)
            raise
        else:
            if cacheable(result):
                self._purge_if_needed()
                self._data[key] = (time.monotonic() + ttl, result)
            fut.set_result(result)
            return result
        finally:
            self._inflight.pop(key, None)

    def _purge_if_needed(self):
        if len(self._data) < _MAX_ENTRIES:
            return
        now = time.monotonic()
        self._data = {k: v for k, v in self._data.items() if v[0] > now}

    def invalidate(self):
        """Drop all cached entries (e.g., after a configuration change)."""
        self._data.clear()
