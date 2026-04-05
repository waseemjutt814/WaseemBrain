from __future__ import annotations

import math

from ..types import EmotionContext


class EmotionFuser:
    def fuse(
        self,
        text_context: EmotionContext | None,
        voice_context: EmotionContext | None,
    ) -> EmotionContext:
        if text_context is None and voice_context is None:
            return {
                "primary_emotion": "neutral",
                "valence": 0.0,
                "arousal": 0.0,
                "confidence": 0.0,
                "source": "both",
            }
        if text_context is None:
            return voice_context  # type: ignore[return-value]
        if voice_context is None:
            return text_context

        dominant = (
            text_context
            if text_context["confidence"] >= voice_context["confidence"]
            else voice_context
        )
        confidence_sum = max(text_context["confidence"] + voice_context["confidence"], 1e-6)
        weighted_valence = (
            text_context["valence"] * text_context["confidence"]
            + voice_context["valence"] * voice_context["confidence"]
        ) / confidence_sum
        return {
            "primary_emotion": dominant["primary_emotion"],
            "valence": weighted_valence,
            "arousal": max(text_context["arousal"], voice_context["arousal"]),
            "confidence": math.sqrt(text_context["confidence"] * voice_context["confidence"]),
            "source": "both",
        }
