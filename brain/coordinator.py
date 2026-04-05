from __future__ import annotations

import asyncio
import re
from collections.abc import AsyncIterator, Callable
from typing import Protocol

from .config import BrainSettings, load_settings
from .dialogue import DialoguePlanner
from .emotion import encode_emotion
from .experts.assembler import ResponseAssembler
from .experts.pool import ExpertPool
from .experts.types import ExpertRequest
from .internet.module import InternetModule
from .learning.features import entity_match_score, query_coverage_score
from .learning.types import TurnTrace
from .learning.feedback import FeedbackCollector
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
    Result,
    RouterDecision,
    SessionId,
)


class RouterClientProtocol(Protocol):
    def decide(
        self, signal: NormalizedSignal, emotion_context: EmotionContext
    ) -> Result[RouterDecision, str]: ...


class LatticeBrainCoordinator:
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
    ) -> None:
        self._settings = settings or load_settings()
        self._memory_graph = memory_graph
        self._expert_pool = expert_pool
        self._router_client = router_client or ArtifactRouterClient(settings=self._settings)
        self._internet_module = internet_module or InternetModule()
        self._feedback_collector = feedback_collector or FeedbackCollector()
        self._response_assembler = response_assembler or ResponseAssembler(settings=self._settings)
        self._dialogue_planner = dialogue_planner or DialoguePlanner(settings=self._settings)
        self._normalizer = normalizer
        self._emotion_encoder = emotion_encoder
        self._recall_limit = recall_limit

    async def process(
        self,
        raw_input: object,
        modality_hint: str,
        session_id: SessionId,
    ) -> AsyncIterator[str]:
        normalized_result = self._normalizer(raw_input, modality_hint, session_id)
        if not normalized_result["ok"]:
            yield normalized_result["error"]
            return
        signal = normalized_result["value"]
        self._memory_graph.ensure_session(session_id)
        emotion_context = self._emotion_encoder(signal)

        router_result = self._router_client.decide(signal, emotion_context)
        if not router_result["ok"]:
            yield router_result["error"]
            return
        decision = router_result["value"]

        memory_nodes = []
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
        if response_plan["mode"] == "clarify":
            clarification = self._dialogue_planner.clarification_prompt(signal, dialogue_state)
            self._feedback_collector.record_turn(
                session_id,
                ExpertId("dialogue-state"),
                query=signal.get("text", ""),
                response=clarification,
                dialogue_intent=dialogue_state["intent"],
                response_mode=response_plan["mode"],
                render_strategy="clarify",
                citations_count=0,
                confidence=dialogue_state["confidence"],
                decision_trace=decision["reasoning_trace"],
                outcome="clarification_requested",
            )
            async for token in self._stream_text(clarification):
                yield token
            return

        internet_citations: list[EvidenceReference] = []
        if decision["internet_needed"]:
            internet_result = await self._internet_module.query(
                signal.get("text", ""), emotion_context["primary_emotion"]
            )
            if internet_result["ok"]:
                internet_citations = internet_result["value"]["citations"]

        expert_request: ExpertRequest = {
            "query": signal.get("text", ""),
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
                query=signal.get("text", ""),
                dialogue_state=dialogue_state,
                response_plan=response_plan,
            )
            if assembled_memory["ok"]:
                self._feedback_collector.record_turn(
                    session_id,
                    assembled_memory["value"]["expert_id"],
                    query=signal.get("text", ""),
                    response=assembled_memory["value"]["content"],
                    dialogue_intent=dialogue_state["intent"],
                    response_mode=response_plan["mode"],
                    render_strategy=assembled_memory["value"]["render_strategy"],
                    citations_count=len(assembled_memory["value"]["citations"]),
                    confidence=assembled_memory["value"]["confidence"],
                    decision_trace=decision["reasoning_trace"],
                    outcome="memory_answered",
                )
                async for token in self._stream_text(assembled_memory["value"]["content"]):
                    yield token
                return
        expert_outputs = await self._expert_pool.infer(decision["experts_needed"], expert_request)
        if not expert_outputs["ok"]:
            self._feedback_collector.record_turn(
                session_id,
                ExpertId("runtime-error"),
                query=signal.get("text", ""),
                response=expert_outputs["error"],
                dialogue_intent=dialogue_state["intent"],
                response_mode="unsupported",
                render_strategy="unsupported",
                citations_count=0,
                confidence=0.0,
                decision_trace=decision["reasoning_trace"],
                outcome="unsupported",
            )
            yield expert_outputs["error"]
            return
        outputs_to_assemble = list(expert_outputs["value"])
        if high_confidence_memory is not None:
            outputs_to_assemble.insert(0, self._memory_to_output(high_confidence_memory))
        assembled = self._response_assembler.assemble(
            outputs_to_assemble,
            query=signal.get("text", ""),
            dialogue_state=dialogue_state,
            response_plan=response_plan,
        )
        if not assembled["ok"]:
            self._feedback_collector.record_turn(
                session_id,
                ExpertId("response-assembler"),
                query=signal.get("text", ""),
                response=assembled["error"],
                dialogue_intent=dialogue_state["intent"],
                response_mode="unsupported",
                render_strategy="unsupported",
                citations_count=0,
                confidence=0.0,
                decision_trace=decision["reasoning_trace"],
                outcome="unsupported",
            )
            yield assembled["error"]
            return

        if assembled["value"]["citations"]:
            self._memory_graph.store(
                assembled["value"]["content"],
                source="expert-answer",
                tags=[],
                session_id=session_id,
                source_type="memory",
                citations=assembled["value"]["citations"],
            )
        self._feedback_collector.record_implicit(
            session_id,
            assembled["value"]["expert_id"],
            "accepted_and_continued",
            "coordinator-default",
            query=signal.get("text", ""),
            response=assembled["value"]["content"],
        )
        self._feedback_collector.record_turn(
            session_id,
            assembled["value"]["expert_id"],
            query=signal.get("text", ""),
            response=assembled["value"]["content"],
            dialogue_intent=dialogue_state["intent"],
            response_mode=response_plan["mode"],
            render_strategy=assembled["value"]["render_strategy"],
            citations_count=len(assembled["value"]["citations"]),
            confidence=assembled["value"]["confidence"],
            decision_trace=decision["reasoning_trace"],
            outcome="answered",
        )
        async for token in self._stream_text(assembled["value"]["content"]):
            yield token

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
