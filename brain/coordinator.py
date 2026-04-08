from __future__ import annotations

import asyncio
import re
import time
from collections.abc import AsyncIterator, Callable
from typing import Protocol, TypedDict

from .config import BrainSettings, load_settings
from .dialogue import DialoguePlanner
from .emotion import encode_emotion
from .experts.assembler import ResponseAssembler
from .experts.pool import ExpertPool
from .experts.types import ExpertRequest
from .internet.module import InternetModule
from .learning.features import entity_match_score, query_coverage_score
from .learning.feedback import FeedbackCollector
from .learning.types import TurnTrace
from .memory.graph import MemoryGraph
from .normalizer import normalize
from .router import ArtifactRouterClient
from .types import (
    EmotionContext,
    EvidenceReference,
    ExpertId,
    ExpertOutput,
    MemoryNode,
    NormalizedSignal,
    RenderStrategy,
    ResponseMode,
    Result,
    RouterDecision,
    SessionId,
    err,
    ok,
)

# Default timeout and retry settings
DEFAULT_COORDINATOR_TIMEOUT_SEC = 30.0
INTERNET_RETRY_COUNT = 3
INTERNET_RETRY_DELAY_SEC = 1.0


class CoordinatorTimeoutError(Exception):
    """Raised when coordinator processing times out."""
    def __init__(self, timeout_sec: float, stage: str = "unknown") -> None:
        self.timeout_sec = timeout_sec
        self.stage = stage
        super().__init__(f"Coordinator timed out after {timeout_sec}s during {stage}")


class RouterClientProtocol(Protocol):
    def decide(
        self, signal: NormalizedSignal, emotion_context: EmotionContext
    ) -> Result[RouterDecision, str]: ...


class CoordinatorTurnResult(TypedDict):
    content: str
    citations: list[EvidenceReference]
    expert_id: ExpertId
    confidence: float
    render_strategy: RenderStrategy
    summary: str
    response_mode: ResponseMode
    decision_trace: str
    dialogue_intent: str


class WaseemBrainCoordinator:
    """Coordinator with timeout protection and retry logic."""
    
    def __init__(
        self,
        memory_graph: MemoryGraph,
        expert_pool: ExpertPool,
        router_client: RouterClientProtocol | None = None,
        internet_module: InternetModule | None = None,
        feedback_collector: FeedbackCollector | None = None,
        response_assembler: ResponseAssembler | None = None,
        dialogue_planner: DialoguePlanner | None = None,
        settings: BrainSettings | None = None,
        normalizer: Callable[
            [object, str | None, SessionId | None], Result[NormalizedSignal, str]
        ] = normalize,
        emotion_encoder: Callable[[NormalizedSignal], EmotionContext] = encode_emotion,
        recall_limit: int = 10,
        timeout_sec: float | None = None,
        internet_retry_count: int = INTERNET_RETRY_COUNT,
    ) -> None:
        self._settings = settings or load_settings()
        self._memory_graph = memory_graph
        self._expert_pool = expert_pool
        self._router_client = router_client or ArtifactRouterClient(settings=self._settings)
        self._internet_module = internet_module or InternetModule(settings=self._settings)
        self._feedback_collector = feedback_collector or FeedbackCollector()
        self._response_assembler = response_assembler or ResponseAssembler(settings=self._settings)
        self._dialogue_planner = dialogue_planner or DialoguePlanner(settings=self._settings)
        self._normalizer = normalizer
        self._emotion_encoder = emotion_encoder
        self._recall_limit = recall_limit
        self._timeout_sec = timeout_sec or DEFAULT_COORDINATOR_TIMEOUT_SEC
        self._internet_retry_count = internet_retry_count

    async def process(
        self,
        raw_input: object,
        modality_hint: str,
        session_id: SessionId,
        timeout_sec: float | None = None,
    ) -> AsyncIterator[str]:
        """Process input with optional timeout override."""
        effective_timeout = timeout_sec or self._timeout_sec
        try:
            turn_result = await asyncio.wait_for(
                self.process_turn(raw_input, modality_hint, session_id),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError:
            yield f"Request timed out after {effective_timeout} seconds. Please try again."
            return
        
        if not turn_result["ok"]:
            yield turn_result["error"]
            return
        async for token in self._stream_text(turn_result["value"]["content"]):
            yield token

    async def process_turn(
        self,
        raw_input: object,
        modality_hint: str,
        session_id: SessionId,
    ) -> Result[CoordinatorTurnResult, str]:
        normalized_result = self._normalizer(raw_input, modality_hint, session_id)
        if not normalized_result["ok"]:
            return err(normalized_result["error"])
        return await self.process_signal(normalized_result["value"], session_id)

    async def process_signal(
        self,
        signal: NormalizedSignal,
        session_id: SessionId,
        timeout_sec: float | None = None,
    ) -> Result[CoordinatorTurnResult, str]:
        """Process signal with timeout protection."""
        effective_timeout = timeout_sec or self._timeout_sec
        start_time = time.time()
        
        self._memory_graph.ensure_session(session_id)
        emotion_context = self._emotion_encoder(signal)

        router_result = self._router_client.decide(signal, emotion_context)
        if not router_result["ok"]:
            return err(router_result["error"])
        decision = router_result["value"]
        
        # Check remaining time
        elapsed = time.time() - start_time
        remaining_timeout = max(1.0, effective_timeout - elapsed)

        memory_nodes: list[MemoryNode] = []
        high_confidence_memory: MemoryNode | None = None
        if decision["check_memory_first"]:
            memory_result = self._memory_graph.recall(
                signal.get("text", ""),
                limit=self._recall_limit,
                session_id=session_id,
            )
            if memory_result["ok"]:
                memory_nodes = [
                    node
                    for node in memory_result["value"]
                    if _memory_relevance(signal.get("text", ""), node["content"]) >= 0.15
                ]
                if memory_nodes:
                    top_memory = memory_nodes[0]
                    memory_relevance = _memory_relevance(signal.get("text", ""), top_memory["content"])
                    if top_memory["confidence"] >= 0.8 and memory_relevance >= 0.35:
                        high_confidence_memory = top_memory

        dialogue_state = self._dialogue_planner.build_state(signal, emotion_context, memory_nodes)
        response_plan = self._dialogue_planner.build_plan(
            signal,
            dialogue_state,
            router_confidence=decision["confidence"],
            has_evidence=bool(memory_nodes),
            has_memory_answer=(
                high_confidence_memory is not None and not decision["internet_needed"]
            ),
        )
        query_text = signal.get("text", "")

        if response_plan["mode"] == "clarify":
            clarification = self._dialogue_planner.clarification_prompt(signal, dialogue_state)
            self._feedback_collector.record_turn(
                session_id,
                ExpertId("dialogue-state"),
                query=query_text,
                response=clarification,
                dialogue_intent=dialogue_state["intent"],
                response_mode=response_plan["mode"],
                render_strategy="clarify",
                citations_count=0,
                confidence=dialogue_state["confidence"],
                decision_trace=decision["reasoning_trace"],
                outcome="clarification_requested",
            )
            return ok(
                {
                    "content": clarification,
                    "citations": [],
                    "expert_id": ExpertId("dialogue-state"),
                    "confidence": dialogue_state["confidence"],
                    "render_strategy": "clarify",
                    "summary": "Clarification requested",
                    "response_mode": response_plan["mode"],
                    "decision_trace": decision["reasoning_trace"],
                    "dialogue_intent": dialogue_state["intent"],
                }
            )

        internet_citations: list[EvidenceReference] = []
        if decision["internet_needed"]:
            internet_result = await self._query_internet_with_retry(
                query_text,
                emotion_context["primary_emotion"],
            )
            if internet_result["ok"]:
                internet_citations = internet_result["value"]["citations"]

        expert_request: ExpertRequest = {
            "query": query_text,
            "session_id": session_id,
            "memory_nodes": memory_nodes,
            "internet_citations": internet_citations,
            "dialogue_state": dialogue_state,
            "response_plan": response_plan,
        }

        if high_confidence_memory is not None and not decision["internet_needed"]:
            memory_output = self._memory_to_output(high_confidence_memory)
            assembled_memory = self._response_assembler.assemble(
                [memory_output],
                query=query_text,
                dialogue_state=dialogue_state,
                response_plan=response_plan,
            )
            if assembled_memory["ok"]:
                value = assembled_memory["value"]
                self._feedback_collector.record_turn(
                    session_id,
                    value["expert_id"],
                    query=query_text,
                    response=value["content"],
                    dialogue_intent=dialogue_state["intent"],
                    response_mode=response_plan["mode"],
                    render_strategy=value["render_strategy"],
                    citations_count=len(value["citations"]),
                    confidence=value["confidence"],
                    decision_trace=decision["reasoning_trace"],
                    outcome="memory_answered",
                )
                return ok(
                    {
                        "content": value["content"],
                        "citations": value["citations"],
                        "expert_id": value["expert_id"],
                        "confidence": value["confidence"],
                        "render_strategy": value["render_strategy"],
                        "summary": value["summary"],
                        "response_mode": response_plan["mode"],
                        "decision_trace": decision["reasoning_trace"],
                        "dialogue_intent": dialogue_state["intent"],
                    }
                )

        expert_outputs = await self._expert_pool.infer(decision["experts_needed"], expert_request)
        if not expert_outputs["ok"]:
            self._feedback_collector.record_turn(
                session_id,
                ExpertId("runtime-error"),
                query=query_text,
                response=expert_outputs["error"],
                dialogue_intent=dialogue_state["intent"],
                response_mode="unsupported",
                render_strategy="unsupported",
                citations_count=0,
                confidence=0.0,
                decision_trace=decision["reasoning_trace"],
                outcome="unsupported",
            )
            return err(expert_outputs["error"])

        outputs_to_assemble = list(expert_outputs["value"])
        if high_confidence_memory is not None:
            outputs_to_assemble.insert(0, self._memory_to_output(high_confidence_memory))

        assembled = self._response_assembler.assemble(
            outputs_to_assemble,
            query=query_text,
            dialogue_state=dialogue_state,
            response_plan=response_plan,
        )
        if not assembled["ok"]:
            self._feedback_collector.record_turn(
                session_id,
                ExpertId("response-assembler"),
                query=query_text,
                response=assembled["error"],
                dialogue_intent=dialogue_state["intent"],
                response_mode="unsupported",
                render_strategy="unsupported",
                citations_count=0,
                confidence=0.0,
                decision_trace=decision["reasoning_trace"],
                outcome="unsupported",
            )
            return err(assembled["error"])

        value = assembled["value"]
        if value["citations"]:
            self._memory_graph.store(
                value["content"],
                source="expert-answer",
                tags=[],
                session_id=session_id,
                source_type="memory",
                citations=value["citations"],
            )
        self._feedback_collector.record_implicit(
            session_id,
            value["expert_id"],
            "accepted_and_continued",
            "coordinator-default",
            query=query_text,
            response=value["content"],
        )
        self._feedback_collector.record_turn(
            session_id,
            value["expert_id"],
            query=query_text,
            response=value["content"],
            dialogue_intent=dialogue_state["intent"],
            response_mode=response_plan["mode"],
            render_strategy=value["render_strategy"],
            citations_count=len(value["citations"]),
            confidence=value["confidence"],
            decision_trace=decision["reasoning_trace"],
            outcome="answered",
        )
        return ok(
            {
                "content": value["content"],
                "citations": value["citations"],
                "expert_id": value["expert_id"],
                "confidence": value["confidence"],
                "render_strategy": value["render_strategy"],
                "summary": value["summary"],
                "response_mode": response_plan["mode"],
                "decision_trace": decision["reasoning_trace"],
                "dialogue_intent": dialogue_state["intent"],
            }
        )

    def flush_session_traces(self, session_id: SessionId) -> list[TurnTrace]:
        return self._feedback_collector.flush_traces(session_id)

    def reload_learned_policies(self) -> None:
        self._dialogue_planner.reload_policy()
        self._response_assembler.reload_policy()

    async def _stream_text(self, text: str) -> AsyncIterator[str]:
        for chunk in text.split():
            yield f"{chunk} "
            await asyncio.sleep(0)

    def _memory_to_output(self, node: MemoryNode) -> ExpertOutput:
        citations: list[EvidenceReference] = [
            {
                "id": provenance["source_id"],
                "source_type": provenance["source_type"],
                "label": provenance["label"],
                "snippet": provenance["snippet"],
                "uri": provenance["uri"],
            }
            for provenance in node["provenance"]
        ]
        return {
            "expert_id": ExpertId("memory-recall"),
            "content": node["content"],
            "confidence": node["confidence"],
            "sources": [citation["label"] for citation in citations],
            "latency_ms": 0.0,
            "citations": citations,
            "render_strategy": "memory",
            "summary": "Session memory recall",
        }
    
    async def _query_internet_with_retry(
        self,
        query: str,
        emotion: str,
    ) -> Result[dict, str]:
        """Query internet with exponential backoff retry."""
        last_error: str = ""
        for attempt in range(self._internet_retry_count):
            try:
                result = await self._internet_module.query(query, emotion)
                if result["ok"]:
                    return result
                last_error = result.get("error", "Unknown internet query error")
            except Exception as exc:
                last_error = str(exc)
            
            # Exponential backoff: 1s, 2s, 4s...
            if attempt < self._internet_retry_count - 1:
                delay = INTERNET_RETRY_DELAY_SEC * (2 ** attempt)
                await asyncio.sleep(delay)
        
        
        # Try to return cached results from memory as fallback
        memory_result = self._memory_graph.recall(query, limit=5)
        if memory_result["ok"] and memory_result["value"]:
            # Return memory results as internet citations
            cached_citations: list[EvidenceReference] = [
                {
                    "id": str(node["id"]),
                    "source_type": node["source_type"],
                    "label": node["source"],
                    "snippet": node["content"][:200],
                    "uri": f"memory://{node['id']}",
                }
                for node in memory_result["value"][:3]
            ]
            return ok({
                "citations": cached_citations,
                "from_cache": True,
                "cache_reason": f"Internet query failed after {self._internet_retry_count} retries: {last_error}",
            })
        
        
        return err(f"Internet query failed after {self._internet_retry_count} retries: {last_error}")
    
    def timeout_settings(self) -> dict[str, float]:
        """Return timeout settings for monitoring."""
        return {
            "timeout_sec": self._timeout_sec,
            "internet_retry_count": self._internet_retry_count,
        }


def _memory_relevance(query: str, content: str) -> float:
    base_score = max(query_coverage_score(query, content), entity_match_score(query, content))
    if base_score > 0.0:
        return base_score
    query_tokens = {token.lower() for token in _MEMORY_TOKEN_PATTERN.findall(query)}
    if query_tokens and query_tokens <= _GREETING_TOKENS:
        content_tokens = {token.lower() for token in _MEMORY_TOKEN_PATTERN.findall(content)}
        overlap = len(query_tokens & content_tokens)
        if overlap > 0:
            return round(overlap / len(query_tokens), 4)
    return 0.0


_MEMORY_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_./-]{2,}")
_GREETING_TOKENS = {"hello", "hi", "hey", "salam"}
