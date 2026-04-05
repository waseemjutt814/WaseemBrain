from __future__ import annotations

from typing import Literal, TypedDict

from ..types import ExpertId, RenderStrategy, SessionId


class FeedbackSignal(TypedDict):
    session_id: SessionId
    expert_id: ExpertId
    query: str
    response: str
    signal_type: Literal["positive", "negative", "neutral"]
    strength: float
    timestamp: float
    evidence: str


class TurnTrace(TypedDict):
    session_id: SessionId
    expert_id: ExpertId
    query: str
    response: str
    dialogue_intent: str
    response_mode: str
    render_strategy: RenderStrategy
    citations_count: int
    has_next_step: bool
    query_coverage: float
    entity_match_score: float
    symbol_anchor_score: float
    response_length_tokens: int
    confidence: float
    decision_trace: str
    outcome: Literal["answered", "memory_answered", "clarification_requested", "unsupported"]
    timestamp: float


class CorrectionJob(TypedDict):
    session_id: SessionId
    expert_id: ExpertId
    negative_examples: list[tuple[str, str]]
    score: float
