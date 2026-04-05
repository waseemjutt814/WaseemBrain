from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from math import sqrt
from pathlib import Path

from .features import entity_match_score, query_coverage_score, symbol_anchor_score
from .types import TurnTrace


@dataclass(frozen=True)
class CandidateRankerProfile:
    citation_weight: float
    next_step_weight: float
    confidence_weight: float
    entity_match_weight: float
    length_weight: float
    query_coverage_weight: float
    symbol_anchor_weight: float
    target_length_tokens: int
    length_tolerance_tokens: int

    @classmethod
    def load(cls, payload: dict[str, object]) -> CandidateRankerProfile:
        return cls(
            citation_weight=_coerce_float(payload.get("citation_weight"), 0.0),
            next_step_weight=_coerce_float(payload.get("next_step_weight"), 0.0),
            confidence_weight=_coerce_float(payload.get("confidence_weight"), 0.0),
            entity_match_weight=_coerce_float(payload.get("entity_match_weight"), 0.0),
            length_weight=_coerce_float(payload.get("length_weight"), 0.0),
            query_coverage_weight=_coerce_float(payload.get("query_coverage_weight"), 0.0),
            symbol_anchor_weight=_coerce_float(payload.get("symbol_anchor_weight"), 0.0),
            target_length_tokens=_coerce_int(payload.get("target_length_tokens"), 48),
            length_tolerance_tokens=max(
                _coerce_int(payload.get("length_tolerance_tokens"), 18),
                6,
            ),
        )

    def adjustment(
        self,
        *,
        citations_count: int,
        has_next_step: bool,
        confidence: float,
        entity_match_score: float,
        query_coverage: float,
        symbol_anchor_score: float,
        response_length_tokens: int,
    ) -> float:
        citation_score = min(max(citations_count, 0), 3) / 3.0
        next_step_score = 1.0 if has_next_step else 0.0
        confidence_score = max(0.0, min(confidence, 1.0))
        entity_score = max(0.0, min(entity_match_score, 1.0))
        length_score = _length_fitness(
            response_length_tokens,
            self.target_length_tokens,
            self.length_tolerance_tokens,
        )
        query_coverage_score_value = max(0.0, min(query_coverage, 1.0))
        symbol_anchor_value = max(0.0, min(symbol_anchor_score, 1.0))
        return round(
            (self.citation_weight * citation_score)
            + (self.next_step_weight * next_step_score)
            + (self.confidence_weight * confidence_score)
            + (self.entity_match_weight * entity_score)
            + (self.length_weight * length_score)
            + (self.query_coverage_weight * query_coverage_score_value)
            + (self.symbol_anchor_weight * symbol_anchor_value),
            4,
        )


@dataclass(frozen=True)
class ResponsePolicyArtifact:
    version: int
    clarification_confidence_floor: float
    intent_mode_bias: dict[str, dict[str, float]]
    intent_strategy_bias: dict[str, dict[str, dict[str, float]]]
    candidate_ranker_profiles: dict[str, CandidateRankerProfile]
    next_step_intents: tuple[str, ...]
    supportive_intents: tuple[str, ...]
    trained_trace_count: int

    @classmethod
    def load(cls, path: Path) -> ResponsePolicyArtifact:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            version=int(payload.get("version", 1)),
            clarification_confidence_floor=float(payload["clarification_confidence_floor"]),
            intent_mode_bias={
                str(intent): {str(mode): float(score) for mode, score in mode_scores.items()}
                for intent, mode_scores in payload["intent_mode_bias"].items()
            },
            intent_strategy_bias={
                str(intent): {
                    str(mode): {
                        str(strategy): float(score)
                        for strategy, score in strategy_scores.items()
                    }
                    for mode, strategy_scores in mode_scores.items()
                }
                for intent, mode_scores in payload.get("intent_strategy_bias", {}).items()
            },
            candidate_ranker_profiles={
                str(mode): CandidateRankerProfile.load(profile)
                for mode, profile in payload.get("candidate_ranker_profiles", {}).items()
                if isinstance(profile, dict)
            },
            next_step_intents=tuple(str(item) for item in payload.get("next_step_intents", [])),
            supportive_intents=tuple(str(item) for item in payload.get("supportive_intents", [])),
            trained_trace_count=int(payload.get("trained_trace_count", 0)),
        )

    def preferred_mode(self, intent: str) -> str | None:
        scores = self.intent_mode_bias.get(intent, {})
        if not scores:
            return None
        mode, score = max(scores.items(), key=lambda item: item[1])
        if score <= 0.0:
            return None
        return mode

    def wants_next_step(self, intent: str) -> bool:
        return intent in self.next_step_intents

    def prefers_supportive(self, intent: str) -> bool:
        return intent in self.supportive_intents

    def preferred_strategy(self, intent: str, response_mode: str) -> str | None:
        mode_scores = self.intent_strategy_bias.get(intent, {}).get(response_mode, {})
        if not mode_scores:
            return None
        strategy, score = max(mode_scores.items(), key=lambda item: item[1])
        if score <= 0.0:
            return None
        return strategy

    def candidate_score_adjustment(
        self,
        response_mode: str,
        *,
        citations_count: int,
        has_next_step: bool,
        confidence: float,
        entity_match_score: float,
        query_coverage: float,
        symbol_anchor_score: float,
        response_length_tokens: int,
    ) -> float:
        profile = self.candidate_ranker_profiles.get(response_mode)
        if profile is None:
            return 0.0
        return profile.adjustment(
            citations_count=citations_count,
            has_next_step=has_next_step,
            confidence=confidence,
            entity_match_score=entity_match_score,
            query_coverage=query_coverage,
            symbol_anchor_score=symbol_anchor_score,
            response_length_tokens=response_length_tokens,
        )


class ResponsePolicyTrainer:
    def fit(self, traces: list[TurnTrace]) -> ResponsePolicyArtifact:
        prepared = [
            trace
            for trace in traces
            if trace["query"].strip() and trace["response"].strip()
        ]
        if len(prepared) < 3:
            raise ValueError("Response policy training requires at least three traces")

        clarification_scores = [
            trace["confidence"]
            for trace in prepared
            if trace["outcome"] == "clarification_requested"
        ]
        clarification_floor = 0.45
        if clarification_scores:
            clarification_floor = min(0.8, max(0.25, _mean(clarification_scores) + 0.05))

        intent_mode_scores: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        intent_strategy_scores: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        mode_ranker_traces: dict[str, list[TurnTrace]] = defaultdict(list)
        next_step_support: dict[str, list[int]] = defaultdict(list)
        supportive_support: dict[str, list[int]] = defaultdict(list)

        for trace in prepared:
            trace_score = _trace_score(trace)
            intent_mode_scores[trace["dialogue_intent"]][trace["response_mode"]].append(
                trace_score
            )
            intent_strategy_scores[trace["dialogue_intent"]][trace["response_mode"]][
                trace["render_strategy"]
            ].append(trace_score)
            mode_ranker_traces[trace["response_mode"]].append(trace)
            next_step_support[trace["dialogue_intent"]].append(
                1
                if (
                    trace["outcome"] in {"answered", "memory_answered"}
                    and trace["citations_count"] > 0
                )
                else 0
            )
            supportive_support[trace["dialogue_intent"]].append(
                1 if trace["outcome"] in {"clarification_requested", "unsupported"} else 0
            )

        return ResponsePolicyArtifact(
            version=4,
            clarification_confidence_floor=clarification_floor,
            intent_mode_bias={
                intent: {
                    mode: round(_mean(scores), 4)
                    for mode, scores in sorted(mode_scores.items())
                }
                for intent, mode_scores in sorted(intent_mode_scores.items())
            },
            intent_strategy_bias={
                intent: {
                    mode: {
                        strategy: round(_mean(scores), 4)
                        for strategy, scores in sorted(strategy_scores.items())
                    }
                    for mode, strategy_scores in sorted(mode_scores.items())
                }
                for intent, mode_scores in sorted(intent_strategy_scores.items())
            },
            candidate_ranker_profiles={
                mode: _fit_ranker_profile(mode_traces)
                for mode, mode_traces in sorted(mode_ranker_traces.items())
                if len(mode_traces) >= 2
            },
            next_step_intents=tuple(
                intent
                for intent, support in sorted(next_step_support.items())
                if _mean(support) >= 0.5
            ),
            supportive_intents=tuple(
                intent
                for intent, support in sorted(supportive_support.items())
                if _mean(support) >= 0.4
            ),
            trained_trace_count=len(prepared),
        )


class ResponsePolicyExporter:
    def export_model(self, output_path: Path, artifact: ResponsePolicyArtifact) -> Path:
        payload = {
            "version": artifact.version,
            "clarification_confidence_floor": artifact.clarification_confidence_floor,
            "intent_mode_bias": artifact.intent_mode_bias,
            "intent_strategy_bias": artifact.intent_strategy_bias,
            "candidate_ranker_profiles": {
                mode: {
                    "citation_weight": profile.citation_weight,
                    "next_step_weight": profile.next_step_weight,
                    "confidence_weight": profile.confidence_weight,
                    "entity_match_weight": profile.entity_match_weight,
                    "length_weight": profile.length_weight,
                    "query_coverage_weight": profile.query_coverage_weight,
                    "symbol_anchor_weight": profile.symbol_anchor_weight,
                    "target_length_tokens": profile.target_length_tokens,
                    "length_tolerance_tokens": profile.length_tolerance_tokens,
                }
                for mode, profile in artifact.candidate_ranker_profiles.items()
            },
            "next_step_intents": list(artifact.next_step_intents),
            "supportive_intents": list(artifact.supportive_intents),
            "trained_trace_count": artifact.trained_trace_count,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return output_path


def load_response_policy(path: Path) -> ResponsePolicyArtifact | None:
    if not path.exists():
        return None
    return ResponsePolicyArtifact.load(path)


def _trace_score(trace: TurnTrace) -> float:
    base = {
        "answered": 1.0,
        "memory_answered": 0.9,
        "clarification_requested": -0.3,
        "unsupported": -0.8,
    }[trace["outcome"]]
    citation_bonus = min(trace["citations_count"], 3) * 0.1
    confidence_weight = 0.5 + (max(min(trace["confidence"], 1.0), 0.0) * 0.5)
    return (base + citation_bonus) * confidence_weight


def _mean(values: list[float] | list[int]) -> float:
    return sum(values) / max(len(values), 1)


def _fit_ranker_profile(traces: list[TurnTrace]) -> CandidateRankerProfile:
    trace_scores = [_trace_score(trace) for trace in traces]
    response_lengths = [max(trace["response_length_tokens"], 1) for trace in traces]
    positive_weights = [max(score + 1.0, 0.1) for score in trace_scores]
    target_length = max(round(_weighted_mean(response_lengths, positive_weights)), 8)
    tolerance = max(
        round(_mean([abs(length - target_length) for length in response_lengths]) + 6),
        8,
    )
    citation_values = [min(trace["citations_count"], 3) / 3.0 for trace in traces]
    next_step_values = [1.0 if trace["has_next_step"] else 0.0 for trace in traces]
    confidence_values = [max(0.0, min(trace["confidence"], 1.0)) for trace in traces]
    query_coverage_values = [
        max(
            0.0,
            min(
                trace.get(
                    "query_coverage",
                    query_coverage_score(trace["query"], trace["response"]),
                ),
                1.0,
            ),
        )
        for trace in traces
    ]
    entity_match_values = [
        max(
            0.0,
            min(
                trace.get(
                    "entity_match_score",
                    entity_match_score(trace["query"], trace["response"]),
                ),
                1.0,
            ),
        )
        for trace in traces
    ]
    symbol_anchor_values = [
        max(
            0.0,
            min(
                trace.get(
                    "symbol_anchor_score",
                    symbol_anchor_score(trace["query"], trace["response"]),
                ),
                1.0,
            ),
        )
        for trace in traces
    ]
    length_values = [
        _length_fitness(trace["response_length_tokens"], target_length, tolerance)
        for trace in traces
    ]
    return CandidateRankerProfile(
        citation_weight=_scaled_correlation(citation_values, trace_scores),
        next_step_weight=_scaled_correlation(next_step_values, trace_scores),
        confidence_weight=_scaled_correlation(confidence_values, trace_scores),
        entity_match_weight=_scaled_correlation(entity_match_values, trace_scores),
        length_weight=_scaled_correlation(length_values, trace_scores),
        query_coverage_weight=_scaled_correlation(query_coverage_values, trace_scores),
        symbol_anchor_weight=_scaled_correlation(symbol_anchor_values, trace_scores),
        target_length_tokens=target_length,
        length_tolerance_tokens=tolerance,
    )


def _length_fitness(length: int, target_length: int, tolerance: int) -> float:
    if tolerance <= 0:
        return 0.0
    distance = abs(max(length, 1) - target_length)
    return max(0.0, 1.0 - (distance / tolerance))


def _weighted_mean(values: list[int], weights: list[float]) -> float:
    total_weight = sum(weights)
    if total_weight <= 0.0:
        return _mean(values)
    return sum(value * weight for value, weight in zip(values, weights, strict=True)) / total_weight


def _scaled_correlation(values: list[float], targets: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean_value = _mean(values)
    mean_target = _mean(targets)
    numerator = sum(
        (value - mean_value) * (target - mean_target)
        for value, target in zip(values, targets, strict=True)
    )
    value_denominator = sqrt(sum((value - mean_value) ** 2 for value in values))
    target_denominator = sqrt(sum((target - mean_target) ** 2 for target in targets))
    if value_denominator == 0.0 or target_denominator == 0.0:
        return 0.0
    correlation = numerator / (value_denominator * target_denominator)
    return round(max(min(correlation, 1.0), -1.0) * 0.35, 4)


def _coerce_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return default
    return default
