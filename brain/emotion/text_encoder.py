from __future__ import annotations

import math
import os
from collections.abc import Callable
from typing import Any, ClassVar, cast

from ..types import EmotionContext, EmotionName, NormalizedSignal

_POSITIVE_WORDS = {"good", "great", "happy", "love", "excellent", "awesome", "thanks"}
_NEGATIVE_WORDS = {"bad", "terrible", "hate", "awful", "wrong", "angry", "sad"}
_EMOTION_KEYWORDS: dict[str, set[str]] = {
    "joy": {"happy", "joy", "love", "delighted", "excited"},
    "sadness": {"sad", "down", "upset", "cry", "lonely"},
    "anger": {"angry", "furious", "mad", "annoyed", "terrible"},
    "fear": {"afraid", "fear", "scared", "worried", "anxious"},
    "surprise": {"wow", "surprised", "unexpected", "suddenly"},
    "disgust": {"gross", "disgusting", "nasty"},
    "confused": {"how", "why", "confused", "unclear", "help"},
}


class TextEmotionEncoder:
    _classifier_pipeline: ClassVar[Any | None] = None
    _classifier_state: ClassVar[str] = "uninitialized"
    _sentiment_analyzer: ClassVar[Any | None] = None
    _sentiment_state: ClassVar[str] = "uninitialized"

    def __init__(
        self,
        vader_backend: Callable[[str], float] | None = None,
        classifier_backend: Callable[[str], dict[str, float]] | None = None,
        backend_preference: str | None = None,
    ) -> None:
        self._vader_backend = vader_backend or self._default_valence
        self._classifier_backend = classifier_backend or self._default_probabilities
        self._backend_preference = (
            backend_preference or os.environ.get("EMOTION_TEXT_BACKEND", "auto")
        ).strip().lower()

    def encode(self, signal: NormalizedSignal) -> EmotionContext:
        text = signal.get("text", "").strip()
        if not text:
            return self._build_context("neutral", 0.0, 0.0, 0.0)

        vader_score = self._vader_backend(text)
        probabilities = self._classifier_backend(text)
        primary_emotion = max(probabilities, key=lambda label: probabilities[label])
        proxy_valence = self._emotion_to_valence(primary_emotion)
        final_valence = (vader_score * 0.6) + (proxy_valence * 0.4)
        confidence = probabilities[primary_emotion]
        arousal = min(1.0, max(abs(vader_score), confidence + (0.2 if "!" in text else 0.0)))
        return self._build_context(primary_emotion, final_valence, arousal, confidence)

    def _default_valence(self, text: str) -> float:
        analyzer = self._load_sentiment_analyzer()
        if analyzer is None:
            words = [token.strip(".,!?;:").lower() for token in text.split()]
            positive = sum(word in _POSITIVE_WORDS for word in words)
            negative = sum(word in _NEGATIVE_WORDS for word in words)
            intensity = min(1.0, (positive + negative) / max(len(words), 1))
            polarity = positive - negative
            if polarity == 0:
                return 0.0
            return math.copysign(intensity, polarity)
        return float(analyzer.polarity_scores(text)["compound"])

    def _default_probabilities(self, text: str) -> dict[str, float]:
        if self._backend_preference == "heuristic":
            return self._heuristic_probabilities(text)

        classifier = self._load_classifier()
        if classifier is None:
            return self._heuristic_probabilities(text)

        try:
            predictions = classifier(text)
        except Exception:
            return self._heuristic_probabilities(text)

        if not predictions or not isinstance(predictions, list):
            return self._heuristic_probabilities(text)
        first_prediction = predictions[0]
        if not isinstance(first_prediction, list):
            return self._heuristic_probabilities(text)
        raw_scores: dict[str, float] = {}
        for item in cast(list[dict[str, Any]], first_prediction):
            label = item.get("label")
            score = item.get("score")
            if not isinstance(label, str) or not isinstance(score, (float, int)):
                continue
            raw_scores[label.lower()] = float(score)
        if not raw_scores:
            return self._heuristic_probabilities(text)
        return self._normalize_scores(raw_scores)

    def _heuristic_probabilities(self, text: str) -> dict[str, float]:
        words = {token.strip(".,!?;:").lower() for token in text.split()}
        scores = {label: 0.05 for label in _EMOTION_KEYWORDS}
        for label, keywords in _EMOTION_KEYWORDS.items():
            scores[label] += sum(0.2 for keyword in keywords if keyword in words)
        if text.endswith("?"):
            scores["confused"] += 0.2
        if "!" in text:
            scores["joy"] += 0.1
            scores["anger"] += 0.1
        if max(scores.values()) <= 0.05:
            return {"neutral": 1.0}
        return self._normalize_scores(scores)

    def _normalize_scores(self, scores: dict[str, float]) -> dict[str, float]:
        total = sum(max(value, 0.0) for value in scores.values()) or 1.0
        return {label: max(value, 0.0) / total for label, value in scores.items()}

    @classmethod
    def _load_sentiment_analyzer(cls) -> Any | None:
        if cls._sentiment_analyzer is not None:
            return cls._sentiment_analyzer
        if cls._sentiment_state == "unavailable":
            return None
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
        except Exception:
            cls._sentiment_state = "unavailable"
            return None
        cls._sentiment_analyzer = SentimentIntensityAnalyzer()
        cls._sentiment_state = "ready"
        return cls._sentiment_analyzer

    @classmethod
    def _load_classifier(cls) -> Any | None:
        if cls._classifier_pipeline is not None:
            return cls._classifier_pipeline
        if cls._classifier_state == "unavailable":
            return None
        try:
            from transformers import pipeline
        except Exception:
            cls._classifier_state = "unavailable"
            return None

        try:
            cls._classifier_pipeline = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                top_k=None,
                device=-1,
            )
        except Exception:
            cls._classifier_state = "unavailable"
            return None
        cls._classifier_state = "ready"
        return cls._classifier_pipeline

    def _emotion_to_valence(self, emotion: str) -> float:
        if emotion in {"joy", "happy"}:
            return 0.9
        if emotion in {"surprise", "excited"}:
            return 0.2
        if emotion in {"anger", "disgust"}:
            return -0.8
        if emotion in {"sadness", "fear", "sad"}:
            return -0.6
        if emotion == "confused":
            return -0.2
        return 0.0

    def _build_context(
        self,
        primary_emotion: str,
        valence: float,
        arousal: float,
        confidence: float,
    ) -> EmotionContext:
        normalized_emotion = "angry" if primary_emotion == "anger" else primary_emotion
        return {
            "primary_emotion": cast(EmotionName, normalized_emotion),
            "valence": max(-1.0, min(1.0, valence)),
            "arousal": max(0.0, min(1.0, arousal)),
            "confidence": max(0.0, min(1.0, confidence)),
            "source": "text",
        }
