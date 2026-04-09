from __future__ import annotations

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Protocol

from ..config import BrainSettings, load_settings
from ..types import (
    DialogueState,
    ExpertId,
    ExpertOutput,
    ResponsePlan,
    Result,
    SessionId,
    err,
    ok,
)
from .expert import Expert
from .registry import ExpertRegistry
from .types import ExpertRequest

# Constants for better code quality
EVICTOR_INTERVAL_SEC = 10
DEFAULT_MAX_TOKENS = 256
DEFAULT_INFERENCE_TIMEOUT_SEC = 30.0


class ExpertPoolError(Exception):
    """Base exception for expert pool operations."""
    pass


class ExpertLoadError(ExpertPoolError):
    """Raised when an expert cannot be loaded."""
    def __init__(self, expert_id: ExpertId, reason: str) -> None:
        self.expert_id = expert_id
        super().__init__(f"Failed to load expert {expert_id}: {reason}")


class ExpertInferenceTimeout(ExpertPoolError):
    """Raised when expert inference times out."""
    def __init__(self, expert_id: ExpertId, timeout_sec: float) -> None:
        self.expert_id = expert_id
        self.timeout_sec = timeout_sec
        super().__init__(f"Expert {expert_id} inference timed out after {timeout_sec}s")


class ExpertMapperProtocol(Protocol):
    def map_expert(self, expert_id: ExpertId, file_path: Path) -> Result[bool, str]: ...

    def evict_expert(self, expert_id: ExpertId) -> Result[bool, str]: ...


class ExpertPool:
    """Thread-safe pool of experts with automatic idle eviction and timeout support."""
    
    def __init__(
        self,
        settings: BrainSettings | None = None,
        registry: ExpertRegistry | None = None,
        executor: ThreadPoolExecutor | None = None,
        mapper: ExpertMapperProtocol | None = None,
        inference_timeout_sec: float | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._registry = registry or ExpertRegistry(self._settings)
        self._executor = executor or ThreadPoolExecutor(
            max_workers=self._settings.expert_max_loaded
        )
        self._mapper = mapper
        self._loaded: dict[str, Expert] = {}
        self._lock = asyncio.Lock()
        self._eviction_task: asyncio.Task[None] | None = None
        self._shutdown = False
        self._inference_timeout_sec = (
            inference_timeout_sec 
            if inference_timeout_sec is not None 
            else DEFAULT_INFERENCE_TIMEOUT_SEC
        )
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            self._eviction_task = loop.create_task(self._run_idle_evictor())

    async def load_async(self, expert_id: ExpertId) -> Result[Expert, str]:
        """Thread-safe async load of an expert."""
        async with self._lock:
            return self._load_unsafe(expert_id)
    
    def load(self, expert_id: ExpertId) -> Result[Expert, str]:
        """Load an expert (sync wrapper for backward compatibility)."""
        existing = self._loaded.get(str(expert_id))
        if existing is not None:
            existing.preload()
            return ok(existing)
        return self._load_unsafe(expert_id)
    
    def _load_unsafe(self, expert_id: ExpertId) -> Result[Expert, str]:
        """Internal load without lock - caller must handle synchronization.
        
        This method handles eviction atomically within the lock to prevent
        race conditions where multiple threads could try to evict the same expert.
        """
        existing = self._loaded.get(str(expert_id))
        if existing is not None:
            existing.preload()
            return ok(existing)

        registry_result = self._registry.get(expert_id)
        if not registry_result["ok"]:
            return registry_result
        
        # Atomic eviction check and action
        if len(self._loaded) >= self._settings.expert_max_loaded:
            self._evict_oldest_unsafe()

        meta = registry_result["value"]
        artifact_root = self._registry.resolve_artifact_root(meta)
        expert = Expert(
            meta,
            artifact_root,
            settings=self._settings,
        )
        expert.preload()
        self._loaded[str(expert_id)] = expert
        if self._mapper is not None:
            mapped_artifact = self._registry.resolve_artifact_path(meta, meta["artifacts"][0])
            self._mapper.map_expert(expert_id, mapped_artifact)
        return ok(expert)
    
    def _evict_oldest_unsafe(self) -> ExpertId | None:
        """Evict the oldest expert atomically. Must be called with lock held.
        
        Returns the ID of the evicted expert, or None if no experts to evict.
        """
        if not self._loaded:
            return None
        oldest_id = min(self._loaded, key=lambda item: self._loaded[item].last_used_at())
        expert_to_unload = self._loaded.pop(oldest_id)
        self._evict_expert(ExpertId(oldest_id))
        expert_to_unload.unload()
        return ExpertId(oldest_id)

    async def infer(
        self,
        expert_ids: list[ExpertId],
        request: ExpertRequest | str,
        timeout_sec: float | None = None,
    ) -> Result[list[ExpertOutput], str]:
        """Run inference on multiple experts with timeout protection.
        
        Args:
            expert_ids: List of expert IDs to run inference on
            request: The inference request (can be string for legacy compatibility)
            timeout_sec: Optional timeout override (uses default if not provided)
            
        Returns:
            Result containing list of expert outputs or error message
        """
        if not expert_ids:
            return ok([])
        
        effective_timeout = timeout_sec if timeout_sec is not None else self._inference_timeout_sec
        
        normalized_request: ExpertRequest
        if isinstance(request, str):
            default_state: DialogueState = {
                "intent": "general",
                "style": "concise",
                "needs_clarification": False,
                "prefers_steps": False,
                "references_workspace": False,
                "references_memory": False,
                "asks_for_reasoning": False,
                "confidence": 0.5,
                "signals": [],
                "locale": "en",
            }
            default_plan: ResponsePlan = {
                "mode": "answer",
                "lead_style": "concise",
                "include_sources": False,
                "include_next_step": False,
                "max_citations": 0,
                "rationale": "legacy request path",
                "locale": "en",
            }
            normalized_request = {
                "query": request,
                "session_id": SessionId("legacy-session"),
                "memory_nodes": [],
                "internet_citations": [],
                "dialogue_state": default_state,
                "response_plan": default_plan,
            }
        else:
            normalized_request = request.copy()
            if "dialogue_state" in normalized_request:
                if "locale" not in normalized_request["dialogue_state"]:
                    normalized_request["dialogue_state"] = {**normalized_request["dialogue_state"], "locale": "en"}
            if "response_plan" in normalized_request:
                if "locale" not in normalized_request["response_plan"]:
                    normalized_request["response_plan"] = {**normalized_request["response_plan"], "locale": "en"}

        loop = asyncio.get_running_loop()
        experts: list[Expert] = []
        for expert_id in expert_ids:
            loaded = await self.load_async(expert_id)
            if not loaded["ok"]:
                return err(loaded["error"])
            experts.append(loaded["value"])

        async def run_expert_with_timeout(expert: Expert) -> Result[ExpertOutput, str]:
            """Run single expert inference with timeout."""
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor,
                        expert.infer,
                        normalized_request["query"],
                        256,
                        normalized_request,
                    ),
                    timeout=effective_timeout,
                )
                return result
            except asyncio.TimeoutError:
                return err(f"Expert {expert._meta['id']} inference timed out after {effective_timeout}s")

        tasks = [run_expert_with_timeout(expert) for expert in experts]
        raw_results = await asyncio.gather(*tasks)
        outputs: list[ExpertOutput] = []
        for result in raw_results:
            if not result["ok"]:
                return err(result["error"])
            outputs.append(result["value"])
        return ok(outputs)

    async def evict_idle_async(self) -> list[ExpertId]:
        """Thread-safe async eviction of idle experts."""
        async with self._lock:
            return self._evict_idle_unsafe()
    
    def evict_idle(self) -> list[ExpertId]:
        """Evict idle experts (sync wrapper)."""
        return asyncio.run(self.evict_idle_async())
    
    def _evict_idle_unsafe(self) -> list[ExpertId]:
        """Internal eviction without lock."""
        now = time.time()
        evicted: list[ExpertId] = []
        for expert_id, expert in list(self._loaded.items()):
            if now - expert.last_used_at() > self._settings.expert_idle_timeout_sec:
                self._evict_expert(ExpertId(expert_id))
                expert.unload()
                del self._loaded[expert_id]
                evicted.append(ExpertId(expert_id))
        return evicted

    def loaded_count(self) -> int:
        return len(self._loaded)

    def loaded_ids(self) -> list[ExpertId]:
        return [ExpertId(expert_id) for expert_id in self._loaded]

    def status(self) -> dict[str, object]:
        """Return current pool status."""
        return {
            "loaded_count": len(self._loaded),
            "loaded_ids": [str(eid) for eid in self._loaded],
            "shutdown": self._shutdown,
        }

    def close(self) -> None:
        """Gracefully shutdown the pool with proper resource cleanup."""
        self._shutdown = True
        if self._eviction_task is not None:
            self._eviction_task.cancel()
            try:
                # Give task a chance to finish gracefully
                asyncio.get_running_loop().run_until_complete(self._eviction_task)
            except (asyncio.CancelledError, RuntimeError):
                pass
            self._eviction_task = None
        for expert_id, expert in list(self._loaded.items()):
            self._evict_expert(ExpertId(expert_id))
            expert.unload()
        self._loaded.clear()
        # Shutdown executor with cancel_futures=True for immediate cleanup
        # This prevents hanging on pending tasks during shutdown
        self._executor.shutdown(wait=True, cancel_futures=True)

    async def _run_idle_evictor(self) -> None:
        """Background task for idle eviction with proper cancellation."""
        while not self._shutdown:
            try:
                await asyncio.sleep(EVICTOR_INTERVAL_SEC)
                if not self._shutdown:
                    await self.evict_idle_async()
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue running
                pass

    def _evict_expert(self, expert_id: ExpertId) -> None:
        if self._mapper is not None:
            self._mapper.evict_expert(expert_id)
