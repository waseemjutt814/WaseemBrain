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


class ExpertMapperProtocol(Protocol):
    def map_expert(self, expert_id: ExpertId, file_path: Path) -> Result[bool, str]: ...

    def evict_expert(self, expert_id: ExpertId) -> Result[bool, str]: ...


class ExpertPool:
    def __init__(
        self,
        settings: BrainSettings | None = None,
        registry: ExpertRegistry | None = None,
        executor: ThreadPoolExecutor | None = None,
        mapper: ExpertMapperProtocol | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._registry = registry or ExpertRegistry(self._settings)
        self._executor = executor or ThreadPoolExecutor(
            max_workers=self._settings.expert_max_loaded
        )
        self._mapper = mapper
        self._loaded: dict[str, Expert] = {}
        self._eviction_task: asyncio.Task[None] | None = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            self._eviction_task = loop.create_task(self._run_idle_evictor())

    def load(self, expert_id: ExpertId) -> Result[Expert, str]:
        existing = self._loaded.get(str(expert_id))
        if existing is not None:
            existing.preload()
            return ok(existing)

        registry_result = self._registry.get(expert_id)
        if not registry_result["ok"]:
            return registry_result
        if len(self._loaded) >= self._settings.expert_max_loaded:
            oldest_id = min(self._loaded, key=lambda item: self._loaded[item].last_used_at())
            self._evict_expert(ExpertId(oldest_id))
            self._loaded.pop(oldest_id).unload()

        meta = registry_result["value"]
        artifact_root = self._settings.expert_dir / meta["artifact_root"]
        expert = Expert(
            meta,
            artifact_root,
            settings=self._settings,
        )
        expert.preload()
        self._loaded[str(expert_id)] = expert
        if self._mapper is not None:
            mapped_artifact = artifact_root / meta["artifacts"][0]["path"]
            self._mapper.map_expert(expert_id, mapped_artifact)
        return ok(expert)

    async def infer(
        self,
        expert_ids: list[ExpertId],
        request: ExpertRequest | str,
    ) -> Result[list[ExpertOutput], str]:
        if not expert_ids:
            return ok([])
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
            loaded = self.load(expert_id)
            if not loaded["ok"]:
                return err(loaded["error"])
            experts.append(loaded["value"])

        tasks = [
            loop.run_in_executor(
                self._executor,
                expert.infer,
                normalized_request["query"],
                256,
                normalized_request,
            )
            for expert in experts
        ]
        raw_results = await asyncio.gather(*tasks)
        outputs: list[ExpertOutput] = []
        for result in raw_results:
            if not result["ok"]:
                return err(result["error"])
            outputs.append(result["value"])
        return ok(outputs)

    def evict_idle(self) -> list[ExpertId]:
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

    def close(self) -> None:
        if self._eviction_task is not None:
            self._eviction_task.cancel()
            self._eviction_task = None
        for expert_id, expert in list(self._loaded.items()):
            self._evict_expert(ExpertId(expert_id))
            expert.unload()
        self._loaded.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)

    async def _run_idle_evictor(self) -> None:
        while True:
            await asyncio.sleep(10)
            self.evict_idle()

    def _evict_expert(self, expert_id: ExpertId) -> None:
        if self._mapper is not None:
            self._mapper.evict_expert(expert_id)
