from __future__ import annotations

import asyncio
import time

from ..config import BrainSettings, load_settings
from ..types import EvidenceReference, MemoryNode, Result, err, ok
from .fetcher import ContentFetcher
from .search import DuckDuckGoSearch
from .types import InternetResult


class InternetModule:
    def __init__(
        self,
        enabled: bool | None = None,
        settings: BrainSettings | None = None,
        search: DuckDuckGoSearch | None = None,
        fetcher: ContentFetcher | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._enabled = self._settings.internet_enabled if enabled is None else enabled
        self._search = search or DuckDuckGoSearch(self._settings)
        self._fetcher = fetcher or ContentFetcher(self._settings)

    async def query(self, search_query: str, context: str) -> Result[InternetResult, str]:
        if not self._enabled:
            return err("Internet access is disabled")

        refined_query = self._refine_query(search_query, context)
        search_result = await self._search.search(
            refined_query, min(5, self._settings.internet_max_requests_per_query)
        )
        if not search_result["ok"]:
            return search_result

        fetch_tasks = [self._fetcher.fetch(item["url"]) for item in search_result["value"][:3]]
        fetch_results = await asyncio.gather(*fetch_tasks)
        combined_results = []
        for item in fetch_results:
            if item["ok"]:
                combined_results.append(item["value"])
        if not combined_results:
            return err("Internet query returned no readable content")

        combined_content = "\n\n".join(result["content"] for result in combined_results)
        citations: list[EvidenceReference] = [
            {
                "id": result["url"],
                "source_type": "internet",
                "label": result["title"] or result["url"],
                "snippet": result["content"][:220],
                "uri": result["url"],
            }
            for result in combined_results
        ]
        return ok(
            {
                "query": refined_query,
                "results": combined_results,
                "combined_content": combined_content,
                "sources": [result["url"] for result in combined_results],
                "retrieved_at": time.time(),
                "citations": citations,
            }
        )

    def is_needed(self, memory_result: list[MemoryNode], confidence_threshold: float) -> bool:
        if not memory_result:
            return True
        return max(node["confidence"] for node in memory_result) < confidence_threshold

    def _refine_query(self, search_query: str, context: str) -> str:
        context_tokens = [token for token in context.split()[:6] if token]
        return " ".join([search_query.strip(), *context_tokens]).strip()
