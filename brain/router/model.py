from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from ..types import ExpertId, RouterDecision

_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_./-]{2,}")
_FNV_OFFSET = 1469598103934665603
_FNV_PRIME = 1099511628211


@dataclass(frozen=True)
class RouterArtifact:
    labels: tuple[str, ...]
    feature_count: int
    expert_weights: tuple[tuple[float, ...], ...]
    expert_bias: tuple[float, ...]
    internet_weights: tuple[float, ...]
    internet_bias: float
    confidence_floor: float

    @classmethod
    def load(cls, path: Path) -> RouterArtifact:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            labels=tuple(str(item) for item in payload["labels"]),
            feature_count=int(payload["feature_count"]),
            expert_weights=tuple(
                tuple(float(value) for value in row) for row in payload["expert_weights"]
            ),
            expert_bias=tuple(float(value) for value in payload["expert_bias"]),
            internet_weights=tuple(float(value) for value in payload["internet_weights"]),
            internet_bias=float(payload["internet_bias"]),
            confidence_floor=float(payload.get("confidence_floor", 0.5)),
        )

    def decide(self, text: str) -> RouterDecision:
        features = build_feature_vector(text, self.feature_count)
        scores = [
            _dot(row, features) + bias
            for row, bias in zip(self.expert_weights, self.expert_bias, strict=True)
        ]
        best_index = max(range(len(scores)), key=scores.__getitem__)
        probabilities = _softmax(scores)
        internet_logit = _dot(self.internet_weights, features) + self.internet_bias
        internet_probability = _sigmoid(internet_logit)
        return {
            "experts_needed": [ExpertId(self.labels[best_index])],
            "check_memory_first": True,
            "internet_needed": internet_probability >= 0.5,
            "confidence": max(self.confidence_floor, probabilities[best_index]),
            "reasoning_trace": (
                f"artifact-router:label={self.labels[best_index]}:"
                f"internet={internet_probability:.3f}"
            ),
        }


def tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())


def build_feature_vector(text: str, feature_count: int) -> list[float]:
    vector = [0.0] * feature_count
    for token in tokenize(text):
        digest = _fnv1a(token)
        index = digest % feature_count
        sign = -1.0 if digest & (1 << 63) else 1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _fnv1a(token: str) -> int:
    value = _FNV_OFFSET
    for byte in token.encode("utf-8"):
        value ^= byte
        value = (value * _FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return value


def _dot(left: tuple[float, ...] | list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def _softmax(values: list[float]) -> list[float]:
    maximum = max(values)
    scaled = [math.exp(value - maximum) for value in values]
    total = sum(scaled) or 1.0
    return [value / total for value in scaled]
