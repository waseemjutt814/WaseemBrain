from __future__ import annotations

import asyncio
import inspect
import time
import logging
from collections import deque
from collections.abc import Callable
from urllib.parse import urlparse

from ..config import BrainSettings, load_settings
from ..types import Result, err, ok
from .types import SearchResult


class DuckDuckGoSearch:
    def __init__(
        self,
        settings: BrainSettings | None = None,
        backend: Callable[[str, int], list[SearchResult]] | None = None,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], object] | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._backend = backend or self._default_backend
        self._clock = clock or time.time
        self._sleeper = sleeper
        self._events: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def search(self, query: str, max_results: int) -> Result[list[SearchResult], str]:
        await self._enforce_rate_limit()
        try:
            results = await asyncio.to_thread(self._backend, query, max_results)
        except Exception as exc:
            return err(f"Search failed: {exc}")

        allowed = self._settings.internet_allowed_domains
        if allowed:
            allowed_set = {domain.lower() for domain in allowed}
            results = [
                result
                for result in results
                if urlparse(result["url"]).netloc.lower() in allowed_set
            ]
        return ok(results[:max_results])

    async def _enforce_rate_limit(self) -> None:
        async with self._lock:
            now = self._clock()
            while self._events and now - self._events[0] >= 60.0:
                self._events.popleft()
            if len(self._events) >= 5:
                wait_seconds = 60.0 - (now - self._events[0])
                if wait_seconds > 0:
                    await self._sleep(wait_seconds)
                now = self._clock()
                while self._events and now - self._events[0] >= 60.0:
                    self._events.popleft()
            self._events.append(self._clock())

    async def _sleep(self, seconds: float) -> None:
        if self._sleeper is None:
            await asyncio.sleep(seconds)
            return
        maybe_awaitable = self._sleeper(seconds)
        if inspect.isawaitable(maybe_awaitable):
            await maybe_awaitable

    def _default_backend(self, query: str, max_results: int) -> list[SearchResult]:
        try:
            from duckduckgo_search import DDGS
        except Exception as e:
            logging.debug(f"DuckDuckGo search unavailable (running without API dependencies): {e}")
            return []

        with DDGS() as client:
            raw_results = list(client.text(query, max_results=max_results))
        return [
            {
                "url": str(item.get("href", "")),
                "title": str(item.get("title", "")),
                "snippet": str(item.get("body", "")),
            }
            for item in raw_results
        ]
