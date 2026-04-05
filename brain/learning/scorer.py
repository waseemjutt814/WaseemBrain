from __future__ import annotations

from .types import FeedbackSignal, TurnTrace


class ResponseScorer:
    def score(self, signals: list[FeedbackSignal], traces: list[TurnTrace] | None = None) -> float:
        positive_weight = sum(
            signal["strength"] for signal in signals if signal["signal_type"] == "positive"
        )
        negative_weight = sum(
            signal["strength"] for signal in signals if signal["signal_type"] == "negative"
        )
        trace_bonus = 0.0
        trace_penalty = 0.0
        for trace in traces or []:
            if trace["outcome"] in {"answered", "memory_answered"} and trace["citations_count"] > 0:
                trace_bonus += 0.15
            if trace["outcome"] in {"clarification_requested", "unsupported"}:
                trace_penalty += 0.2
        raw_score = (positive_weight + trace_bonus - negative_weight - trace_penalty) / (
            positive_weight + negative_weight + trace_bonus + trace_penalty + 1.0
        )
        return max(-1.0, min(1.0, raw_score))

    def needs_correction(self, score: float) -> bool:
        return score < -0.3
