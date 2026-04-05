from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import SGDClassifier  # type: ignore[import-untyped]

from .model import build_feature_vector


@dataclass(frozen=True)
class RouterTrainingSample:
    text: str
    labels: list[str]
    internet_needed: bool = False


@dataclass(frozen=True)
class TrainedRouterModel:
    labels: list[str]
    feature_count: int
    expert_weights: list[list[float]]
    expert_bias: list[float]
    internet_weights: list[float]
    internet_bias: float
    confidence_floor: float


class RouterTrainer:
    def __init__(self, feature_count: int = 1024) -> None:
        self._feature_count = feature_count

    def prepare_dataset(self, samples: list[RouterTrainingSample]) -> list[RouterTrainingSample]:
        prepared: list[RouterTrainingSample] = []
        for sample in samples:
            labels = [label for label in sample.labels if label.strip()]
            if not sample.text.strip() or not labels:
                continue
            prepared.append(
                RouterTrainingSample(
                    text=sample.text.strip(),
                    labels=[labels[0]],
                    internet_needed=bool(sample.internet_needed),
                )
            )
        return prepared

    def fit(self, samples: list[RouterTrainingSample]) -> TrainedRouterModel:
        prepared = self.prepare_dataset(samples)
        if len(prepared) < 3:
            raise ValueError("Router training requires at least three labeled samples")

        matrix = np.array(
            [build_feature_vector(sample.text, self._feature_count) for sample in prepared],
            dtype=np.float64,
        )
        expert_targets = np.array([sample.labels[0] for sample in prepared])
        expert_classifier = SGDClassifier(
            loss="log_loss",
            max_iter=4000,
            tol=1e-4,
            random_state=0,
        )
        expert_classifier.fit(matrix, expert_targets)

        internet_targets = np.array([int(sample.internet_needed) for sample in prepared])
        internet_classifier = SGDClassifier(
            loss="log_loss",
            max_iter=4000,
            tol=1e-4,
            random_state=0,
        )
        internet_classifier.fit(matrix, internet_targets)

        return TrainedRouterModel(
            labels=[str(label) for label in expert_classifier.classes_],
            feature_count=self._feature_count,
            expert_weights=expert_classifier.coef_.astype(float).tolist(),
            expert_bias=expert_classifier.intercept_.astype(float).tolist(),
            internet_weights=internet_classifier.coef_[0].astype(float).tolist(),
            internet_bias=float(internet_classifier.intercept_[0]),
            confidence_floor=0.5,
        )
