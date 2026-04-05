from __future__ import annotations

import time
from collections import defaultdict
from typing import Literal

from ..types import ExpertId, RenderStrategy, SessionId
from .features import entity_match_score, query_coverage_score, symbol_anchor_score
from .types import FeedbackSignal, TurnTrace

_SIGNAL_STRENGTHS = {
    "clarification_needed": 0.4,
    "rephrased_same_question": 0.7,
    "contradiction_in_followup": 0.9,
    "accepted_and_continued": 0.3,
}


class FeedbackCollector:
    def __init__(self) -> None:
        self._signals: dict[str, list[FeedbackSignal]] = defaultdict(list)
        self._traces: dict[str, list[TurnTrace]] = defaultdict(list)

    def record_explicit(
        self, session_id: SessionId, expert_id: ExpertId, is_positive: bool
    ) -> None:
        signal: FeedbackSignal = {
            "session_id": session_id,
            "expert_id": expert_id,
            "query": "",
            "response": "",
            "signal_type": "positive" if is_positive else "negative",
            "strength": 1.0,
            "timestamp": time.time(),
            "evidence": "explicit-feedback",
        }
        self._signals[str(session_id)].append(signal)

    def record_implicit(
        self,
        session_id: SessionId,
        expert_id: ExpertId,
        signal_type: str,
        evidence: str,
        *,
        query: str = "",
        response: str = "",
    ) -> None:
        strength = _SIGNAL_STRENGTHS.get(signal_type, 0.1)
        polarity: Literal["positive", "negative"] = (
            "positive" if signal_type == "accepted_and_continued" else "negative"
        )
        signal: FeedbackSignal = {
            "session_id": session_id,
            "expert_id": expert_id,
            "query": query,
            "response": response,
            "signal_type": polarity,
            "strength": strength,
            "timestamp": time.time(),
            "evidence": evidence,
        }
        self._signals[str(session_id)].append(signal)

    def record_turn(
        self,
        session_id: SessionId,
        expert_id: ExpertId,
        *,
        query: str,
        response: str,
        dialogue_intent: str,
        response_mode: str,
        render_strategy: RenderStrategy,
        citations_count: int,
        confidence: float,
        decision_trace: str,
        outcome: Literal[
            "answered", "memory_answered", "clarification_requested", "unsupported"
        ],
    ) -> None:
        query_coverage = query_coverage_score(query, response)
        entity_match = entity_match_score(query, response)
        symbol_anchor = symbol_anchor_score(query, response)
        trace: TurnTrace = {
            "session_id": session_id,
            "expert_id": expert_id,
            "query": query,
            "response": response,
            "dialogue_intent": dialogue_intent,
            "response_mode": response_mode,
            "render_strategy": render_strategy,
            "citations_count": citations_count,
            "has_next_step": "Next useful step:" in response,
            "query_coverage": query_coverage,
            "entity_match_score": entity_match,
            "symbol_anchor_score": symbol_anchor,
            "response_length_tokens": len(response.split()),
            "confidence": confidence,
            "decision_trace": decision_trace,
            "outcome": outcome,
            "timestamp": time.time(),
        }
        self._traces[str(session_id)].append(trace)

    def flush(self, session_id: SessionId) -> list[FeedbackSignal]:
        return self._signals.pop(str(session_id), [])

    def flush_traces(self, session_id: SessionId) -> list[TurnTrace]:
        return self._traces.pop(str(session_id), [])
